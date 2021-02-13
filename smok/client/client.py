import datetime
import io
import os
import tempfile
import threading
import time
import typing as tp
import uuid
import weakref
from abc import ABCMeta

import pytz
from satella.coding import Closeable, for_argument
from satella.coding.concurrent import PeekableQueue
from satella.coding.structures import DirtyDict

from .api import RequestsAPI
from .certificate import get_device_info, get_root_cert, get_dev_ca_cert
from .slave import SlaveDevice
from ..baob import BAOB
from ..basics import DeviceInfo, Environment, StorageLevel
from ..exceptions import ResponseError, UnavailableError
from ..extras import BaseSensorDatabase, BaseEventDatabase, BaseMacroDatabase, \
    BasePathpointDatabase, BaseMetadataDatabase, BaseBAOBDatabase, BaseArchivesDatabase, \
    BaseSensorWriteDatabase
from ..extras.arch_database.in_memory import InMemoryArchivesDatabase
from ..extras.baob_database.memory import InMemoryBAOBDatabase
from ..extras.event_database import InMemoryEventDatabase
from ..extras.macros_database.in_memory import InMemoryMacroDatabase
from ..extras.metadata_database import InMemoryMetadataDatabase
from ..extras.pp_database.in_memory import InMemoryPathpointDatabase
from ..extras.sensor_write_database.in_memory import InMemorySensorWriteDatabase
from ..extras.sensors_database.in_memory import InMemorySensorDatabase
from ..metadata import PlainMetadata
from ..pathpoint import Pathpoint, ReparsePathpoint
from ..pathpoint.orders import Section, MessageOrder
from ..predicate import BaseStatistic, Event, Color
from ..sensor import Sensor, fqtsify, SensorWriteEvent
from ..threads import OrderExecutorThread, CommunicatorThread, ArchivingAndMacroThread, \
    LogPublisherThread
import logging


logger = logging.getLogger(__name__)


class SMOKDevice(Closeable, metaclass=ABCMeta):
    """
    A base class for a SMOK device.

    You should subclass it, to provide your own device.

    Note that instantiating this object spawns two non-daemon thread. This object must be
    close()d before termination (or garbage collected).

    :param cert: either a path to or a file-like object containing the device certificate
    :param priv_key: either a path to or a file-like object containing the device private key
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
    :param arch_database: custom archives database. Default value of None will result in an
        in-memory implementation
    :param sensor_write_database: custom sensor write database. Default value of None will result in
        an in-memory implementation
    :param dont_obtain_orders: if set to True, this SMOKDevice won't poll for orders.
        This also implies dont_do_baobs. It is a ValueError to set this while setting
        dont_bo_baobs to False.
    :param dont_do_pathpoints: if set to True, this SMOKDevice won't support pathpoints
        or sensors.
    :param dont_sync_sensor_writes: if set to True, sensor writes won't be synced
    :param dont_do_baobs: if set to True, this SMOKDevice won't care about BAOBs.
    :param dont_do_macros: if set to True, this SMOKDevice won't take care of the macros
    :param dont_do_predicates: if set to True, this SMOKDevice won't do predicates
    :param dont_do_archives: if set to True, this SMOKDevice won't do archiving
    :param startup_delay: amount of seconds to wait after creation for CommunicatorThread to
        start talking
    :param cache_metadata_for: amount of seconds to cache downloaded metadata entry.
        Ie no attempt to download them from the server again will be made in that many
        seconds since the download.

    About 10 seconds from creation if CommunicatorThread was created, sensors will be synced and
    the device will start talking. To reduce this delay, set parameter startup_delay

    If both dont_do_macros and dont_do_archives are True, the archiving & macro thread
    won't be started.
    If dont_obtain_orders is True, then order executor and order getter threads won't be started.

    :ivar device_id: device ID of this device
    :ivar environment: environment of this device
    :ivar pathpoints: a dictionary, keying pathpoint names to their instances
    :ivar url: base URL for the API calls, without the trailing slash
    :ivar metadata: plain metadata for this device
        (class :class:`smokclient.metadata.PlainMetadata`)
    :ivar baobs_loaded: whether all BAOBS have been synchronized (bool)

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
        raise KeyError()

    def sync_sections(self, termination_checker: tp.Callable[[], bool]):
        """
        A CANNOT_JOIN section is about to be executed.

        This needs to block until all orders issued up to this point are finished.

        Called by the order executor thread, that's why it can safely block.

        Sections should be synchronized in bounded time.

        Override this method. Default does nothing.

        :param termination_checker: a callable that can be called to determine whether given
            SMOKDevice is undergoing a shutdown. If this callable starts to return True,
            the function should return.
        """

    def execute_section(self, section: Section) -> None:
        """
        Overload to implement custom section execution.

        If this is not overloaded, standard executor logic will be applied.

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
                 arch_database: tp.Optional[BaseArchivesDatabase] = None,
                 sensor_write_database: tp.Optional[BaseSensorWriteDatabase] = None,
                 dont_obtain_orders: bool = False,
                 dont_sync_sensor_writes: bool = False,
                 dont_do_macros: bool = False,
                 dont_do_predicates: bool = False,
                 dont_do_pathpoints: bool = False,
                 dont_do_baobs: bool = False,
                 dont_do_archives: bool = False,
                 cache_metadata_for: float = 60,
                 startup_delay: float = 10):
        super().__init__()
        self.cache_metadata_for = cache_metadata_for
        self.dont_do_predicates = dont_do_predicates
        self.dont_do_pathpoints = dont_do_pathpoints
        self.dont_sync_sensor_writes = dont_sync_sensor_writes
        self.pp_database = pp_database or InMemoryPathpointDatabase()
        self.baobs_loaded = False
        if isinstance(evt_database, str):
            self.evt_database = InMemoryEventDatabase(evt_database)
        else:
            self.evt_database = evt_database
        self.macros_database = macro_database or InMemoryMacroDatabase()
        self.meta_database = meta_database or InMemoryMetadataDatabase()
        self.sensor_database = sensor_database or InMemorySensorDatabase()
        self.sensor_database.on_register(self)
        self.arch_database = arch_database or InMemoryArchivesDatabase()
        self.baob_database = baob_database or InMemoryBAOBDatabase()
        self.sensor_write_database = sensor_write_database or InMemorySensorWriteDatabase()
        self.metadata = PlainMetadata(self)
        self.ready_lock = threading.Lock()
        self.ready_lock.acquire()
        self.predicates = {}  # type: tp.Dict[str, BaseStatistic]
        self._timezone = None
        self.predicate_classes = {}  # type: tp.Dict[str, tp.Type[BaseStatistic]]
        self._statistics_updated = False
        self.pathpoints = DirtyDict()  # type: tp.Dict[str, Pathpoint]
        self.temp_file_for_cert = None
        if not isinstance(cert, str):
            with tempfile.NamedTemporaryFile('w', delete=False) as cert_file:
                cert_file.write(cert.read())
            cert = self.temp_file_for_cert = cert_file.name

        self.temp_file_for_key = None
        if not isinstance(priv_key, str):
            with tempfile.NamedTemporaryFile('w', delete=False) as key_file:
                key_file.write(priv_key.read())
            priv_key = self.temp_file_for_key = key_file.name

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
            self.url = 'http://api.test.smok-serwis.pl'
        elif self.environment == Environment.LOCAL_DEVELOPMENT:
            self.url = 'http://http-api'

        self.api = RequestsAPI(self)

        self._order_queue = PeekableQueue()
        if not (dont_do_archives and dont_do_macros):
            self.arch_and_macros = ArchivingAndMacroThread(self, self._order_queue,
                                                           dont_do_macros, dont_do_archives).start()
        else:
            self.arch_and_macros = None
        self.dont_do_baobs = dont_do_baobs
        if not dont_obtain_orders or not dont_do_predicates or not dont_do_pathpoints or \
                not dont_do_baobs:
            self.executor = OrderExecutorThread(self, self._order_queue, self.pp_database).start()
            self.getter = CommunicatorThread(self, self._order_queue, self.pp_database,
                                             dont_obtain_orders,
                                             dont_do_baobs,
                                             dont_do_pathpoints,
                                             dont_do_predicates,
                                             dont_sync_sensor_writes, startup_delay).start()
        else:
            self.executor = None
            self.getter = None
        self.log_publisher = LogPublisherThread(self).start()

    def log_sensor_write(self, sw: SensorWriteEvent):
        """
        Log that a sensor has been written and enqueue it for cloud upload

        :param sw: sensor write event to upload
        """
        self.sensor_write_database.add_sw(sw)

    def get_baob(self, key: str) -> BAOB:
        """
        Retrieve given BAOB

        :raises UnavailableError: client was launched in a mode with BAOBs disabled
        """
        if self.dont_do_baobs:
            raise UnavailableError('Support for BAOBs was disabled')
        return BAOB(self, key)

    def get_all_baobs(self) -> tp.Iterator[BAOB]:
        """
        Stream all BAOBs

        :raises UnavailableError: client was launched in a mode with BAOBs disabled
        """
        if self.dont_do_baobs:
            raise UnavailableError('Support for BAOBs was disabled')

        for key in self.baob_database.get_all_keys():
            yield BAOB(self, key)

    def wait_until_synced(self) -> None:
        """Block until everything's synchronized with the server"""
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
            except ResponseError:
                pass

    @property
    def timezone(self) -> pytz.timezone:
        """
        :return: the timezone this device is in
        """
        if self._timezone is None:
            self.get_device_info()
        return pytz.timezone(self._timezone)

    def close_event(self, event: Event) -> None:
        """
            Close the provided event

        :param event: event to close
        """
        assert not event.is_closed()
        if event.ended_on is None:
            event.ended_on = time.time()
        self.evt_database.close_event(event)

    def get_open_event(self, event_id: str) -> Event:
        """
        Return a particular opened event

        :param event_id: opened event UUID
        :return: a particular event
        :raises KeyError: event not found, or already closed
        :rtype: Event
        :raise UnavailableError: SMOKDevice was launched in a no-predicate mode
        """
        if self.dont_do_predicates:
            raise UnavailableError('SMOKDevice was launched without predicates')
        for event in self.evt_database.get_open_events():
            if event.uuid_matches(event_id):
                return event
        raise KeyError()

    def get_all_sensors(self) -> tp.Iterator[Sensor]:
        """
        Stream all sensors

        .. note:: This will block until sensors are synced from the server

        :raise UnavailableError: SMOKDevice was launched in a no-pathpoint mode
        """
        if self.dont_do_pathpoints:
            raise UnavailableError('SMOKDevice was launched without pathpoints')
        with self.ready_lock:
            yield from self.sensor_database.get_all_sensors()

    def get_sensor(self, tag_set: tp.Union[tp.Set[str], str]) -> Sensor:
        """
        Return a sensor

        .. note:: This will block until sensors are synced from the server

        :param tag_set: either set of strs or these strs joined with a ' '
        :return: sensor
        :raises KeyError: sensor does not exist
        :raise UnavailableError: SMOKDevice was launched in a no-pathpoint mode
        """
        if self.dont_do_pathpoints:
            raise UnavailableError('SMOKDevice was launched without pathpoints')
        with self.ready_lock:
            if isinstance(tag_set, set):
                tag_set = list(tag_set)
                tag_set.sort()
                tag_set = ' '.join(tag_set)
            else:
                tag_set = fqtsify(tag_set)
            return self.sensor_database.get_sensor(tag_set)

    def get_all_open_events(self) -> tp.Iterator[Event]:
        """
        Get all open events

        :raise UnavailableError: SMOKDevice was launched in a no-predicate mode
        """
        if self.dont_do_predicates:
            raise UnavailableError('SMOKDevice was launched without predicates')
        return self.evt_database.get_open_events()

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
        :param metadata: extra metadata
        :return: the Event object
        :raise UnavailableError: SMOKDevice was launched in a no-predicate mode
        """
        if self.dont_do_predicates:
            raise UnavailableError('SMOKDevice was launched without predicates')
        metadata = metadata or {}
        evt_uuid = uuid.uuid4().hex
        event = Event(evt_uuid, started_on, ended_on, color, is_point, token, group, message,
                      None, metadata)
        self.evt_database.add_event(event)
        return event

    def execute(self, *secs: Section) -> None:
        """
        Schedule sections to be executed

        :param secs: sections to be executed, in that order, unless they're joinable
        """
        for sec in secs:
            self._order_queue.put(sec)

    def get_pathpoint(self, path: str,
                      storage_level: StorageLevel = StorageLevel.TREND) -> Pathpoint:
        """
        Obtain a pathpoint. Creates one and registers it if not available.

        :param path: path of the pathpoint
        :param storage_level: target storage level
        :return: a pathpoint having provided name
        :raises KeyError: pathpoint not available
        :raise UnavailableError: SMOKDevice was launched in a no-pathpoint mode
        """
        if self.dont_do_pathpoints:
            raise UnavailableError('SMOKDevice was launched without pathpoints')
        if path[0] == 'r':
            return ReparsePathpoint(self, path, storage_level)
        if path in self.pathpoints:
            return self.pathpoints[path]
        pp = self.provide_unknown_pathpoint(path, storage_level)  # raises KeyError
        self.register_pathpoint(pp)
        return pp

    def register_statistic(self, stat: tp.Type[BaseStatistic]) -> None:
        """
        Register a new statistic.

        Statistics can be registered at any point. If there are pending predicates,
        instances will be created for them shortly by the communicator thread.

        :param stat: a class (not an instance) to register

        :raise UnavailableError: SMOKDevice was launched in a no-predicate mode
        """
        if self.dont_do_predicates:
            raise UnavailableError('SMOKDevice was launched without predicates')
        assert issubclass(stat, BaseStatistic), 'Not a subclass of BaseStatistic!'
        self.predicate_classes[stat.statistic_name] = stat

    def register_pathpoint(self, pp: Pathpoint) -> None:
        """
        Register a pathpoint for usage with this SMOKDevice.

        Normally, you shouldn't need to use it, as the :class:`~smokclient.pathpoint.Pathpoint`
        constructor does that for you. However, if you provide it's `SMOKDevice` parameter as None,
        this call is still required

        :param pp: pathpoint to register
        :raise UnavailableError: SMOKDevice was launched in a no-pathpoint mode
        """
        if self.dont_do_pathpoints:
            raise UnavailableError('SMOKDevice was launched without pathpoints')
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
        """
        if super().close():
            if self.executor is not None:
                self.executor.terminate()
                self.getter.terminate()
            self.log_publisher.terminate()
            if self.arch_and_macros is not None:
                self.arch_and_macros.terminate()
            if self.temp_file_for_cert:
                os.unlink(self.temp_file_for_cert)
            if self.temp_file_for_key:
                os.unlink(self.temp_file_for_key)
            if self.executor is not None:
                self.executor.join()
                self.getter.join()
            self.log_publisher.join()
            if self.arch_and_macros is not None:
                self.arch_and_macros.join()

    @for_argument(returns=list)
    def get_slaves(self) -> tp.List[SlaveDevice]:
        """
        Return information about slave devices

        :return: a list of slave devices
        :raises ResponseError: server responded (or not) with an invalid message
        """
        slaves = self.get_device_info().slaves
        for slave in slaves:
            yield SlaveDevice(self, slave)

    def get_device_info(self) -> DeviceInfo:
        """
        Obtain information about the device.

        :return: current device information
        :raises ResponseError: server responded (or not) with an invalid message
        """
        resp = DeviceInfo.from_json(self.api.get('/v1/device'))
        self._timezone = resp.timezone
        return resp

    def get_local_time(self) -> datetime.datetime:
        """
        Return current local time on target culture context

        :return: a datetime object having the local time for this device
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
        mydat = self.cert_data
        devcadat = get_dev_ca_cert()
        rootdat = get_root_cert()
        return mydat+devcadat+rootdat

