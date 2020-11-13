import datetime
import io
import os
import tempfile
import threading
import time
import typing as tp
import weakref
from abc import ABCMeta

import pytz
from satella.coding import Closeable, for_argument
from satella.coding.concurrent import PeekableQueue
from satella.coding.structures import DirtyDict

from .api import RequestsAPI
from .certificate import get_device_info
from .slave import SlaveDevice
from ..basics import DeviceInfo, Environment, StorageLevel
from ..extras.event_database import BaseEventDatabase, InMemoryEventDatabase
from ..extras.macros_database import BaseMacroDatabase
from ..extras.macros_database.in_memory import InMemoryMacroDatabase
from ..extras.pp_database.base import BasePathpointDatabase
from ..extras.pp_database.in_memory import InMemoryPathpointDatabase
from ..pathpoint import Pathpoint
from ..pathpoint.orders import Section
from ..predicate import BaseStatistic
from ..predicate.event import Event
from ..sensor import Sensor, fqtsify
from ..threads import OrderExecutorThread, CommunicatorThread, ArchivingAndMacroThread


class SMOKDevice(Closeable, metaclass=ABCMeta):
    """
    A base class for a SMOK device.

    You should subclass it, to provide your own device.

    Note that instantiating this object spawns two non-daemon thread. This object must be
    close()d before termination (or __del__eted).

    :param cert: either a path to or a file-like object containing the device certificate
    :param priv_key: either a path to or a file-like object containing the device private key
    :param evt_database: custom event database. Providing a string defaults to path where predicate
        data will be persisted.
    :param pp_database: custom pathpoint value database. Default value of None defaults to an
        in-memory implementation
    :param macro_database: custom macro database. Default value of None will result in an
        in-memory implementation
    :param dont_obtain_orders: if set to True, this SMOKDevice won't poll for orders
    :param dont_do_macros: if set to True, this SMOKDevice won't take care of the macros
    :param dont_do_archives: if set to True, this SMOKDevice won't do archiving

    If both dont_do_macros and dont_do_archives are True, the archiving & macro thread
    won't be started.

    :ivar device_id: device ID of this device
    :ivar environment: environment of this device
    :ivar pathpoints: a dictionary, keying pathpoint names to their instances
    :ivar url: base URL for the API calls, without the trailing slash
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

    def wait_until_synced(self) -> None:
        """Block until everything's synchronized with the server"""
        self.ready_lock.acquire()
        self.ready_lock.release()

    def __init__(self, cert: tp.Union[str, io.StringIO],
                 priv_key: tp.Union[str, io.StringIO],
                 evt_database: tp.Union[str, BaseEventDatabase],
                 pp_database: tp.Optional[BasePathpointDatabase] = None,
                 macro_database: tp.Optional[BaseMacroDatabase] = None,
                 dont_obtain_orders: bool = False,
                 dont_do_macros: bool = False,
                 dont_do_archives: bool = False):
        super().__init__()
        self.pp_database = pp_database or InMemoryPathpointDatabase()
        if isinstance(evt_database, str):
            self.evt_database = InMemoryEventDatabase(evt_database)
        else:
            self.evt_database = evt_database
        self.macros_database = macro_database or InMemoryMacroDatabase()
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
        self.executor = OrderExecutorThread(self, self._order_queue, self.pp_database).start()
        self.getter = CommunicatorThread(self, self._order_queue, self.pp_database,
                                         dont_obtain_orders).start()
        self.sensors = {}  # type: tp.Dict[str, Sensor]

    @property
    def timezone(self) -> pytz.timezone:
        if self._timezone is None:
            self.get_device_info()
        return pytz.timezone(self._timezone)

    def get_open_event(self, event_id: str) -> Event:
        """
        :return: a particular event
        :raises KeyError: event not found, or already closed
        """
        for event in self.evt_database.get_open_events():
            if event.uuid_matches(event_id):
                return event
        raise KeyError()

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

        :return: a pathpoint having provided name
        :raises KeyError: pathpoint not available
        """
        if path in self.pathpoints:
            return self.pathpoints[path]
        pp = self.provide_unknown_pathpoint(path, storage_level)  # raises KeyError
        self.register_pathpoint(pp)
        return pp

    def register_statistic(self, stat: tp.Type[BaseStatistic]):
        """
        Register a new statistic.

        Statistics can be registered at any point. If there are pending predicates,
        instances will be created for them shortly by the communicator thread.

        :param stat: a class (not an instance) to register
        """
        assert issubclass(stat, BaseStatistic), 'Not a subclass of BaseStatistic!'
        self.predicate_classes[stat.statistic_name] = stat

    def register_pathpoint(self, pp: Pathpoint) -> None:
        """
        Register a pathpoint for usage with this SMOKDevice.

        Normally, you shouldn't need to use it, as the :class:`~smokclient.pathpoint.Pathpoint`
        constructor does that for you. However, if you provide it's `SMOKDevice` parameter as None,
        this call is still required

        :param pp: pathpoint to register
        """
        if pp.name not in self.pathpoints:
            pp.device = weakref.proxy(self)
            self.pathpoints[pp.name] = pp

    def close(self) -> None:
        """
        Close the connection, clean up the resources.

        This may block for up to 10 seconds.
        """
        if super().close():
            self.executor.terminate()
            self.getter.terminate()
            if self.arch_and_macros is not None:
                self.arch_and_macros.terminate()
            if self.temp_file_for_cert:
                os.unlink(self.temp_file_for_cert)
            if self.temp_file_for_key:
                os.unlink(self.temp_file_for_key)
            self.executor.join()
            self.getter.join()
            if self.arch_and_macros is not None:
                self.arch_and_macros.join()

    @for_argument(returns=list)
    def get_slaves(self) -> tp.List[SlaveDevice]:
        slaves = self.get_device_info().slaves
        for slave in slaves:
            yield SlaveDevice(self, slave)

    def get_device_info(self) -> DeviceInfo:
        """
        Obtain information about the device.

        :return: current device information
        :raises ResponseError: server responded with an invalid message
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

    @for_argument(None, fqtsify)
    def get_sensor(self, tag_name: tp.Union[str, tp.Set[str]]) -> Sensor:
        """
        Return a target sensor.

        .. note:: this may block until the Sensors are synced from target server.

        :param tag_name: either words joined by a space of a set of these
        :return: a target Sensor
        :raises KeyError: no target sensor exists
        """
        with self.ready_lock:
            return self.sensors[tag_name]  # raises KeyError
