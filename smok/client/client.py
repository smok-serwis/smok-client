import datetime
import io
import logging
import os
import tempfile
import threading
import time
import typing as tp
import uuid
import warnings
import weakref
from abc import ABCMeta

import pytz
from satella.coding import Closeable, for_argument, wraps
from satella.coding.concurrent import PeekableQueue, Condition
from satella.coding.optionals import Optional
from satella.coding.structures import DirtyDict
from satella.time import time_as_int

from smok.sync_workers.ngtt import NGTTSyncWorker
from smok.sync_workers.http import HTTPSyncWorker
from .api import RequestsAPI
from .certificate import get_device_info, get_root_cert, get_dev_ca_cert
from .slave import SlaveDevice
from ..baob import BAOB
from ..basics import DeviceInfo, Environment, StorageLevel
from ..exceptions import ResponseError, UnavailableError
from ..extras import BaseSensorDatabase, BaseEventDatabase, BaseMacroDatabase, \
    BasePathpointDatabase, BaseMetadataDatabase, BaseBAOBDatabase, BaseArchivesDatabase, \
    BaseSensorWriteDatabase, BasePredicateDatabase
from ..extras.arch_database.in_memory import InMemoryArchivesDatabase
from ..extras.baob_database.memory import InMemoryBAOBDatabase
from ..extras.event_database import InMemoryEventDatabase
from ..extras.macros_database.in_memory import InMemoryMacroDatabase
from ..extras.metadata_database import InMemoryMetadataDatabase
from ..extras.pp_database.in_memory import InMemoryPathpointDatabase
from ..extras.pred_database.in_memory import InMemoryPredicateDatabase
from ..extras.sensor_write_database.in_memory import InMemorySensorWriteDatabase
from ..extras.sensors_database.in_memory import InMemorySensorDatabase
from ..metadata import PlainMetadata
from ..pathpoint import Pathpoint, ReparsePathpoint
from ..pathpoint.orders import Section, MessageOrder
from ..predicate import BaseStatistic, Event, Color
from ..predicate.registration import CollectionOfStatistics, StatisticRegistration
from ..predicate.undefined import UndefinedStatistic
from ..sensor import Sensor, fqtsify, SensorWriteEvent
from ..threads import OrderExecutorThread, CommunicatorThread, ArchivingAndMacroThread, \
    LogPublisherThread
from ..threads.communicator import PREDICATE_SYNC_INTERVAL

logger = logging.getLogger(__name__)


def must_be_open(fun):
    @wraps(fun)
    def inner(self, *args, **kwargs):
        if self.closed:
            raise RuntimeError('SMOK device already closed!')
        return fun(self, *args, **kwargs)
    return inner


class SMOKDevice(Closeable, metaclass=ABCMeta):
    """
    A base class for a SMOK device.

    You should subclass it, to provide your own device.

    Note that instantiating this object spawns two non-daemon thread. This object must be
    close()d before termination (or garbage collected).

    :param cert: either a path to or a file-like object containing the device certificate
    :param priv_key: either a path to or a file-like object containing the device private key
    :param allow_sync: whether to allow outbound TCP communication to automatically synchronize
        background. Note that if you explicitly call a method that calls TCP this does not apply.
        Can be lated changed.
    :param evt_database: custom event database. Providing a string defaults to path where predicate
        data will be persisted. Since events are persistent, a store needs to be given.
    :param pp_database: custom pathpoint value database. Default value of None defaults to an
        in-memory implementation
    :param macro_database: custom macro database. Default value of None will result in an
        in-memory implementation
    :param meta_database: custom meta database. Default value of None will result in an
        in-memory implementation
    :param sensor_database: custom sensor database. Default value of None will result in an
        in-memory implementation
    :param baob_database: custom BAOB database. Default value of None will result in an
        in-memory implementation
    :param pred_database: custom Predicate database. Default value of None will result in an
        in-memory implementation
    :param arch_database: custom archives database. Default value of None will result in an
        in-memory implementation
    :param sensor_write_database: custom sensor write database. Default value of None will result in
        an in-memory implementation
    :param dont_obtain_orders: if set to True, this SMOKDevice won't poll for orders.
        This also implies dont_do_baobs. It is a ValueError to set this while setting
        dont_bo_baobs to False.
    :param dont_do_pathpoints: if set to True, this SMOKDevice won't support pathpoints
        or sensors. By won't support I mean it won't try to synchronize the data,
        but pathpoints and sensors will still be available. Note that providing a source
        of pathpoints in the form of a database is required, and it is a ValueError
        to try to give this to True without giving a sensor_database.
    :param dont_sync_sensor_writes: if set to True, sensor writes won't be synced
    :param dont_do_baobs: if set to True, this SMOKDevice won't care about BAOBs.
    :param dont_do_macros: if set to True, this SMOKDevice won't take care of the macros
    :param dont_do_predicates: if set to True, this SMOKDevice won't do predicates
    :param dont_do_archives: if set to True, this SMOKDevice won't do archiving
    :param startup_delay: amount of seconds to wait after creation for CommunicatorThread to
        start talking and OrderExecutorThread to start grabbing orders. Deprecated.
    :param cache_metadata_for: amount of seconds to cache downloaded metadata entry.
        Ie no attempt to download them from the server again will be made in that many
        seconds since the download.
    :param delayed_boot: if set to True, you will need to call
        :meth:`~smok.client.SMOKDevice.continue_boot` in order to start fetching orders and the
        like. False by default.
    :param use_ngtt: if set to True, logs, orders and pathpoint data will be transmitted over
        a persistent TLS connection instead of HTTP API.


    About 10 seconds from creation if CommunicatorThread was created, sensors will be synced and
    the device will start talking. To reduce this delay, set parameter startup_delay

    If both dont_do_macros and dont_do_archives are True, the archiving & macro thread
    won't be started.
    If dont_obtain_orders is True, then order executor and order getter threads won't be started.

    Every method is supposed to be called from user threads (SMOKDevice's service threads included),
    unless noted otherwise.

    :ivar device_id: device ID of this device (str)
    :ivar allow_sync: whether to allow background synchronization (bool).
        This can be changed by setting it directly to correct value. Setting this to False
        will help you save some bandwidth. Note that log upload will be put on hold, until it
        overflows the buffer. In that case, earlier submitted logs will be thrown on the floor
        to make room for new entries.
    :ivar pathpoints: a dictionary, keying pathpoint names to their instances
    :ivar url: base URL for the API calls, without the trailing slash
    :ivar metadata: plain metadata for this device
        (class :class:`smok.metadata.PlainMetadata`)
    :ivar baobs_loaded: whether all BAOBS have been synchronized (bool)
    :ivar cert_data: (bytes) device certificate as given by the user

    :raise ValueError: invalid combination of arguments was given
    """

    def provide_unknown_pathpoint(self, name: str,
                                  storage_level: StorageLevel = StorageLevel.TREND) -> Pathpoint:
        """
        Override this method to generate pathpoints that are referred to by incoming commands,
        but not defined yet.

        The default implementation always raises `KeyError`.

        .. note:: this can safely raise `KeyError` upon encountering a predicate that is manually
                  defined and registered via :class:`~smokclient.pathpoint.Pathpoint`

        :return: a Pathpoint instance corresponding to what was ordered
        :raises KeyError: pathpoint could not be generated
        """
        return Pathpoint(self, name, storage_level)

    def sync_sections(self, termination_checker: tp.Callable[[], bool]):
        """
        Called by order executor thread before a CANNOT_JOIN section is about to be executed.

        Override this method if you are providing a custom
        :meth:`~smok.client.SMOKDevice.execute_section`. Default does nothing.

        This needs to block until all orders issued up to this point are finished.

        Called by the order executor thread, that's why it can safely block.

        Sections should be synchronized in bounded time.

        :param termination_checker: a callable that can be called to determine whether given
            SMOKDevice is undergoing a shutdown. If this callable starts to return True,
            the function should return at once.
        """

    def execute_section(self, section: Section) -> None:
        """
        Override to implement custom section execution.

        If this is not overridden, standard executor logic will be applied.

        This will not provide you with cancelled sections. You also do not need to mark
        sections as complete, as this is done by the executor thread.

        Called by the order executor thread. If this is defined, then
        :meth:`~smok.client.SMOKDevice.sync_sections` is necessary as well, so this should just
        execute the orders themselves.

        :param section: section to execute
        """

    def __init__(self, cert: tp.Union[str, io.StringIO],
                 priv_key: tp.Union[str, io.StringIO],
                 evt_database: tp.Union[str, BaseEventDatabase],
                 pp_database: tp.Optional[BasePathpointDatabase] = None,
                 macro_database: tp.Optional[BaseMacroDatabase] = None,
                 meta_database: tp.Optional[BaseMetadataDatabase] = None,
                 sensor_database: tp.Optional[BaseSensorDatabase] = None,
                 baob_database: tp.Optional[BaseBAOBDatabase] = None,
                 pred_database: tp.Optional[BasePredicateDatabase] = None,
                 arch_database: tp.Optional[BaseArchivesDatabase] = None,
                 sensor_write_database: tp.Optional[BaseSensorWriteDatabase] = None,
                 allow_sync: bool = True,
                 dont_obtain_orders: bool = False,
                 dont_sync_sensor_writes: bool = False,
                 dont_do_macros: bool = False,
                 dont_do_predicates: bool = False,
                 dont_do_pathpoints: bool = False,
                 dont_do_baobs: bool = False,
                 dont_do_archives: bool = False,
                 cache_metadata_for: float = 60,
                 startup_delay: tp.Optional[float] = None,
                 delayed_boot: bool = False,
                 use_ngtt: bool = False):
        if startup_delay is not None:
            warnings.warn('This is deprecated. Use delayed_boot', DeprecationWarning)
        else:
            startup_delay = 0
        super().__init__()
        Optional(baob_database).check_consistency()
        self.cache_metadata_for = cache_metadata_for
        if dont_do_pathpoints and sensor_database is None:
            raise ValueError('Provide a sensor database if you dont provide pathpoints!')

        self.dont_do_predicates = dont_do_predicates
        self.dont_do_pathpoints = dont_do_pathpoints
        self.dont_sync_sensor_writes = dont_sync_sensor_writes
        self.pp_database = pp_database or InMemoryPathpointDatabase()
        self.baobs_loaded = False
        self.allow_sync = allow_sync
        if isinstance(evt_database, str):
            self.evt_database = InMemoryEventDatabase(evt_database)
        else:
            self.evt_database = evt_database
        self.macros_database = macro_database or InMemoryMacroDatabase()
        self.meta_database = meta_database or InMemoryMetadataDatabase()
        self.pred_database = pred_database or InMemoryPredicateDatabase()
        self.delayed_boot = delayed_boot
        self.sensor_database = sensor_database or InMemorySensorDatabase()
        self.sensor_database.on_register(self)
        self.use_ngtt = use_ngtt
        self.arch_database = arch_database or InMemoryArchivesDatabase()
        self.baob_database = baob_database or InMemoryBAOBDatabase()
        self.sensor_write_database = sensor_write_database or InMemorySensorWriteDatabase()
        self.metadata = PlainMetadata(self)
        self.ready_lock = threading.Lock()
        self.ready_lock.acquire()

        self.predicates = {}  # type: tp.Dict[str, BaseStatistic]

        # Load cached predicates
        for predicate in self.pred_database.get_all_predicates():
            udf = UndefinedStatistic(device=self, **predicate)
            self.predicates[udf.predicate_id] = udf

        self._timezone = None
        self.statistic_registration = CollectionOfStatistics()
        self._statistics_updated = False
        self.pathpoints = DirtyDict()  # type: tp.Dict[str, Pathpoint]
        self.temp_file_for_cert = None
        self.cert_file_name = None
        if not isinstance(cert, str):
            with tempfile.NamedTemporaryFile('w', delete=False) as cert_file:
                cert_file.write(cert.read())
            cert = self.temp_file_for_cert = cert_file.name
        else:
            self.cert_file_name = self.temp_file_for_cert = cert

        self.priv_key_file_name = None
        self.temp_file_for_key = None
        if not isinstance(priv_key, str):
            with tempfile.NamedTemporaryFile('w', delete=False) as key_file:
                key_file.write(priv_key.read())
            priv_key = self.temp_file_for_key = key_file.name
        else:
            self.priv_key_file_name = self.temp_file_for_key = priv_key

        self.cert = cert, priv_key

        with open(cert, 'rb') as fin:
            cert_data = fin.read()

        self.cert_data = cert_data
        dev_id, env = get_device_info(cert_data)
        self.device_id = dev_id  # type: str
        self.environment = env  # type: Environment
        if self.environment == Environment.PRODUCTION:
            self.url = 'https://api.smok.co'
        elif self.environment == Environment.STAGING:
            self.url = 'https://api.test.smok-serwis.pl'
        elif self.environment == Environment.LOCAL_DEVELOPMENT:
            self.url = 'http://http-api'

        self.api = RequestsAPI(self)
        self.log_publisher = LogPublisherThread(self)

        self._order_queue = PeekableQueue()
        if not (dont_do_archives and dont_do_macros):
            self.arch_and_macros = ArchivingAndMacroThread(self, self._order_queue,
                                                           dont_do_macros, dont_do_archives)
            if not delayed_boot:
                self.arch_and_macros.start()
        else:
            self.arch_and_macros = None
        self.dont_do_baobs = dont_do_baobs
        self.dont_do_orders = dont_obtain_orders
        self.executor = None
        self.getter = None
        if not dont_obtain_orders or not dont_do_predicates or not dont_do_pathpoints or \
                not dont_do_baobs:
            self.executor = OrderExecutorThread(self, self._order_queue, self.pp_database,
                                                startup_delay)
            self.getter = CommunicatorThread(self, self._order_queue, self.pp_database,
                                             dont_obtain_orders,
                                             dont_do_baobs,
                                             dont_do_pathpoints,
                                             dont_do_predicates,
                                             dont_sync_sensor_writes, startup_delay)
        else:
            self.ready_lock.release()

        if not delayed_boot:
            if self.use_ngtt:
                self.sync_worker = NGTTSyncWorker(self)
            else:
                self.sync_worker = HTTPSyncWorker(self)
            if not dont_obtain_orders or not dont_do_predicates or not dont_do_pathpoints or \
                    not dont_do_baobs:
                self.executor.start()
                self.getter.start()
            self.log_publisher.start()
            self.boot_completed = True
        else:
            self.sync_worker = None
            self.boot_completed = False

    def continue_boot(self):
        """
        Call this to continue the booting if delayed_start was given in the constructor

        This will start the communicator and order executor thread.

        :raise RuntimeError: delayed boot was not given
        """
        if not self.delayed_boot:
            raise RuntimeError('Delayed boot was not given')
        if self.use_ngtt:
            self.sync_worker = NGTTSyncWorker(self)
        else:
            self.sync_worker = HTTPSyncWorker(self)
        Optional(self.executor).start()
        Optional(self.getter).start()
        Optional(self.arch_and_macros).start()
        self.log_publisher.start()
        self.boot_completed = True

    @must_be_open
    def log_sensor_write(self, sw: SensorWriteEvent):
        """
        Log that a sensor has been written and enqueue it for cloud upload

        :param sw: sensor write event to upload
        :raises RuntimeError: device already closed
        """
        self.sensor_write_database.add_sw(sw)

    @must_be_open
    def reset_predicates(self):
        """
        Clear all loaded predicates and force a renew of loading.

        Discards all currently loaded Predicate instances. Currently registered statistics will
        remain registered.

        .. warning:: Currently requires Internet access to restore predicates
        :raises RuntimeError: device already closed
        """
        self.predicates = {}
        self.getter.last_predicates_synced = time.monotonic() - PREDICATE_SYNC_INTERVAL

    @must_be_open
    def get_baob(self, key: str) -> BAOB:
        """
        Retrieve given BAOB

        :raises UnavailableError: client was launched in a mode with BAOBs disabled
        :raises RuntimeError: device already closed
        """
        if self.dont_do_baobs:
            raise UnavailableError('Support for BAOBs was disabled')
        return BAOB(self, key)

    @must_be_open
    def get_all_baobs(self) -> tp.Iterator[BAOB]:
        """
        Stream all BAOBs

        :raises UnavailableError: client was launched in a mode with BAOBs disabled
        :raises RuntimeError: device already closed
        """
        if self.dont_do_baobs:
            raise UnavailableError('Support for BAOBs was disabled')

        for key in self.baob_database.get_all_keys():
            yield BAOB(self, key)

    def wait_until_synced(self) -> None:
        """
        Block until everything's synchronized with the server.

        Note that this is a no-op if no communicator thread is spawned.
        """
        self.ready_lock.acquire()
        self.ready_lock.release()

    def _execute_message_order(self, order: MessageOrder) -> None:
        """
        Tell the server to execute provided :class:`~smok.pathpoint.orders.MessageOrder`

        :param order: order to execute
        :meta public:
        """
        for i in range(3):
            try:
                self.api.post('/v1/device/orders/message/' + order.uuid)
                self.on_successful_sync()
            except ResponseError as e:
                if e.is_no_link():
                    self.on_failed_sync()

    @property
    def timezone(self) -> pytz.timezone:
        """
        :return: the timezone this device is in
        """
        if self._timezone is None:
            self.get_device_info()
        return pytz.timezone(self._timezone)

    @must_be_open
    def close_event(self, event: Event, timestamp: tp.Optional[int] = None) -> None:
        """
            Close the provided event

        :param event: event to close
        :param timestamp: timestamp of close. Defaults to now
        :raises RuntimeError: device already closed
        """
        assert not event.is_closed()
        if event.ended_on is None:
            event.ended_on = timestamp or time_as_int()
        self.evt_database.close_event(event)

    @must_be_open
    def get_open_event(self, event_id: str) -> Event:
        """
        Return a particular opened event

        :param event_id: opened event UUID
        :return: a particular event
        :raises KeyError: event not found, or already closed
        :rtype: Event
        :raise UnavailableError: SMOKDevice was launched in a no-predicate mode
        :raises RuntimeError: device already closed
        """
        if self.dont_do_predicates:
            raise UnavailableError('SMOKDevice was launched without predicates')
        for event in self.evt_database.get_open_events():
            if event.uuid_matches(event_id):
                return event
        raise KeyError()

    @must_be_open
    def get_all_sensors(self) -> tp.Iterator[Sensor]:
        """
        Stream all sensors

        .. note:: This will block until sensors are synced from the server

        :raises RuntimeError: device already closed
        """
        with self.ready_lock:
            yield from self.sensor_database.get_all_sensors()

    def on_baob_updated(self, baob_name: str) -> None:
        """
        Called by CommunicatorThread after given BAOB was updated.

        After this is called, the new BAOB can be successfully loaded and it's new
        contents will be retrieved.

        This is not invoked during the first synchronization, nor after you change the BAOB
        on the client side.

        :param baob_name: name of the BAOB that was just downloaded from the server
        """

    @must_be_open
    def get_sensor(self, tag_set: tp.Union[tp.Set[str], str]) -> Sensor:
        """
        Return a sensor

        .. note:: This will block until sensors are synced from the server

        :param tag_set: either set of strs or these strs joined with a ' '
        :return: sensor
        :raises KeyError: sensor does not exist
        :raises RuntimeError: device already closed
        """
        with self.ready_lock:
            if isinstance(tag_set, set):
                tag_set = list(tag_set)
                tag_set.sort()
                tag_set = ' '.join(tag_set)
            else:
                tag_set = fqtsify(tag_set)
            return self.sensor_database.get_sensor(tag_set)

    @must_be_open
    def get_all_events(self) -> tp.Iterator[Event]:
        """
        Return all events kept in device's database

        :raise UnavailableError: SMOKDevice was launched in a no-predicate mode
        :raises RuntimeError: device already closed
        """
        if self.dont_do_predicates:
            raise UnavailableError('SMOKDevice was launched without predicates')
        return self.evt_database.get_all_events()

    @must_be_open
    def get_all_open_events(self) -> tp.Iterator[Event]:
        """
        Get all open events

        :raise UnavailableError: SMOKDevice was launched in a no-predicate mode
        :raises RuntimeError: device already closed
        """
        if self.dont_do_predicates:
            raise UnavailableError('SMOKDevice was launched without predicates')
        return self.evt_database.get_open_events()

    @must_be_open
    def open_event(self, started_on: int, ended_on: tp.Optional[int],
                   color: Color, is_point: bool, token: str, group: str, message: str,
                   metadata: tp.Optional[tp.Dict[str, str]] = None) -> Event:
        """
        Create a new event

        :param started_on: timestamp in seconds, when was the event started?
        :param ended_on: timestamp in seconds when has the event ended, None in case of
            open events.
        :param color: :term:`Color` of an event
        :param is_point: whether this is a :term:`point event`
        :param token: a string
        :param group: notification group
        :param message: human-readable message
        :param metadata: extra metadata. This must be dict'able
        :return: the Event object
        :raise UnavailableError: SMOKDevice was launched in a no-predicate mode
        :raises RuntimeError: device already closed
        """
        if self.dont_do_predicates:
            raise UnavailableError('SMOKDevice was launched without predicates')
        metadata = dict(metadata or {})
        evt_uuid = uuid.uuid4().hex
        event = Event(evt_uuid, started_on, ended_on, color, is_point, token, group, message,
                      None, metadata)
        self.evt_database.add_event(event)
        return event

    def execute(self, *secs: Section) -> None:
        """
        Schedule sections to be executed.

        To be invoked by any thread. Use this to inject sections into device's execution loop.

        :param secs: sections to be executed, in that order, unless they're joinable
        """
        for sec in secs:
            self._order_queue.put(sec)

    @must_be_open
    def get_pathpoint(self, path: str,
                      storage_level: StorageLevel = StorageLevel.TREND) -> Pathpoint:
        """
        Obtain a pathpoint. Creates one and registers it if not available.

        :param path: path of the pathpoint
        :param storage_level: target storage level
        :return: a pathpoint having provided name
        :raises KeyError: pathpoint not available
        :raises RuntimeError: device already closed
        """
        if path[0] == 'r':
            return ReparsePathpoint(self, path, storage_level)
        if path in self.pathpoints:
            return self.pathpoints[path]
        pp = self.provide_unknown_pathpoint(path, storage_level)  # raises KeyError
        self.register_pathpoint(pp)
        return pp

    @must_be_open
    def register_statistic(self, stat: tp.Type[BaseStatistic],
                           predicate: tp.Callable[[str, dict], bool]) -> StatisticRegistration:
        """
        Register a new statistic.

        Statistics can be registered at any point. If there are pending predicates,
        instances will be created for them shortly by the communicator thread.

        :param stat: a class (not an instance) to register
        :param predicate: a callable taking two arguments: statistic name and it's configuration.
            The callable should return whether to apply stat to this predicate
        :return: a Registration object. Can be later cancelled.
        :raise UnavailableError: SMOKDevice was launched in a no-predicate mode
        :raises RuntimeError: device already closed
        """
        if self.dont_do_predicates:
            raise UnavailableError('SMOKDevice was launched without predicates')
        assert issubclass(stat, BaseStatistic), 'Not a subclass of BaseStatistic!'
        reg = StatisticRegistration(predicate, stat)
        self.statistic_registration.add(reg)
        return reg

    @must_be_open
    def register_pathpoint(self, pp: Pathpoint) -> None:
        """
        Register a pathpoint for usage with this SMOKDevice.

        Normally, you shouldn't need to use it, as the :class:`~smokclient.pathpoint.Pathpoint`
        constructor does that for you. However, if you provide it's `SMOKDevice` parameter as None,
        this call is still required

        :param pp: pathpoint to register
        :raises RuntimeError: device already closed
        """
        if pp.name[0] == 'r':
            return
        if pp.name not in self.pathpoints:
            pp.device = weakref.proxy(self)
            self.pathpoints[pp.name] = pp

    def execute_sysctl(self, op_type: str, op_args: str) -> bool:
        """
        Called by executor thread upon receiving a request to execute a particular SysctlOrder

        Handles commonly defined BAOBs. Extend to implement custom sysctls.
        Sysctl orders are user-defined.

        :param op_type: type of operation to execute
        :param op_args: argument of the operation to execute.
        :return: whether this command was recognized and acted upon
        """
        if self.dont_do_baobs:
            return False
        if op_type in ('baob-updated', 'baob-created'):
            if self.getter is not None:
                self.getter.last_baob_synced = 0
                self.getter.data_to_update.notify()
            return True
        elif op_type == 'baob-deleted':
            self.baob_database.delete_baob(op_args)
            return True
        return False

    def close(self) -> None:
        """
        Close the connection, clean up the resources.

        This may block for up to 10 seconds.

        No-op if called more than once.
        """
        if super().close():
            Optional(self.executor).terminate()
            Optional(self.getter).terminate()
            self.log_publisher.terminate()
            Optional(self.arch_and_macros).terminate()
            if self.priv_key_file_name is None:
                os.unlink(self.temp_file_for_key)
            if self.cert_file_name is None:
                os.unlink(self.temp_file_for_cert)
            Optional(self.executor).join()
            Optional(self.getter).join()
            if self.boot_completed:
                self.log_publisher.join()
            Optional(self.arch_and_macros).join()

    @must_be_open
    @for_argument(returns=list)
    def get_slaves(self) -> tp.List[SlaveDevice]:
        """
        Return information about slave devices

        :return: a list of slave devices
        :raises ResponseError: server responded (or not) with an invalid message
        :raises RuntimeError: device already closed
        """
        slaves = self.get_device_info().slaves
        for slave in slaves:
            yield SlaveDevice(self, slave)

    @must_be_open
    def get_device_info(self) -> DeviceInfo:
        """
        Obtain information about the device.

        Note that this will result in :meth:`~smok.client.SMOKDevice.on_failed_sync`
        or :meth:`~smok.client.SMOKDevice.on_successful_sync` being called.

        :return: current device information
        :raises ResponseError: server responded (or not) with an invalid message
        :raises RuntimeError: :attr:`~smok.client.SMOKDevice.allow_sync` was set to False or
            device already closed
        """
        if not self.allow_sync:
            raise RuntimeError('allow_sync is False, cannot fetch the information')
        try:
            resp = DeviceInfo.from_json(self.api.get('/v1/device'))
        except ResponseError as e:
            if e.is_no_link():
                self.on_failed_sync()
            raise
        self.on_successful_sync()
        self._timezone = resp.timezone
        return resp

    def on_successful_sync(self, *args, **kwargs) -> None:
        """
        Called by CommunicatorThread each time a part of the system synchronizes correctly with the
        server. Can be used to implement link liveness detector.

        args and kwargs left for future extendability.

        Please note that if you set allow_sync to False this won't be called, as the client won't
        try to talk to the server. The only chance is getting synces manually, as via
        :meth:`~smok.client.SMOKDevice.get_device_info`
        """

    def on_failed_sync(self, *args, **kwargs) -> None:
        """
        Called by CommunicatorThread each time a part of the system fails to synchronize by
        receiving no response at all from the server. Can be used to implement link liveness
        detector.

        args and kwargs left for future extendability

        Please note that if you set allow_sync to False this won't be called, as the client won't
        try to talk to the server. The only chance is getting synces manually, as via
        :meth:`~smok.client.SMOKDevice.get_device_info`
        """

    @must_be_open
    def get_local_time(self) -> datetime.datetime:
        """
        Return current local time on target culture context

        :return: a datetime object having the local time for this device
        :raises RuntimeError: device already closed
        """
        # What is the time on target device?
        tz = self.timezone

        utc_time = pytz.UTC.localize(datetime.datetime.utcfromtimestamp(time.time()))
        local_time = utc_time.astimezone(tz)

        return local_time

    @property
    def cert_chain(self) -> bytes:
        """
        Return your own certificate chain, finishing at SMOK CA certificate

        :return: certificate chain in PEM format
        """
        my_dat = self.cert_data
        dev_ca_dat = get_dev_ca_cert()
        root_ca_dat = get_root_cert()
        return b''.join((my_dat, dev_ca_dat, root_ca_dat))
