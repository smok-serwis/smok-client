import typing as tp
import weakref
from abc import ABCMeta, abstractmethod
from concurrent.futures import Future

from satella.coding import wraps
from satella.coding.structures import ReprableMixin, OmniHashableMixin
from satella.coding.typing import Number

from .orders import AdviseLevel, Section, ReadOrder, WriteOrder
from .typing import PathpointValueType, ValueOrExcept
from ..basics import StorageLevel
from ..exceptions import OperationFailedError, InstanceNotReady


def must_have_device(fun):
    @wraps(fun)
    def inner(self, *args, **kwargs):
        if not self.device:
            raise InstanceNotReady('You need to attach this pathpoint to a device first')
        return fun(self, *args, **kwargs)
    return inner


class Pathpoint(ReprableMixin, OmniHashableMixin, metaclass=ABCMeta):
    """
    Base class for an user-defined pathpoint.

    Note that pathpoint is registered in the device as part of it's creation.

    :param device: device that this pathpoint should be attached to. None is also a valid option.
    :param name: pathpoint name.
    :param storage_level: storage level for this pathpoint

    :ivar name: pathpoint name
    :ivar storage_level: pathpoint's storage level
    :ivar current_timestamp: a timestamp in seconds of the last read
    :ivar current_value: last readed value or an exception instance
    :ivar device: a weak reference to the device
    """
    _HASH_FIELDS_TO_USE = ('name',)
    _REPR_FIELDS = ('name', 'storage_level')
    __slots__ = ('name', 'storage_level', 'current_value', 'current_timestamp', 'device',
                 'is_reparse', 'slave_pathpoints', 'reparse_expr')

    def __init__(self, device: tp.Optional['SMOKDevice'], name: str,
                 storage_level: StorageLevel = StorageLevel.TREND):
        self.device = weakref.proxy(device)
        self.name = name
        self.is_reparse = name[0] == 'r'
        self.storage_level = storage_level
        self.current_value = None  # type: ValueOrExcept
        self.current_timestamp = None  # type: Number
        # noinspection PyProtectedMember
        if device is not None:
            device.register_pathpoint(self)
        if self.is_reparse:
            from ..sensor.reparse import parse
            self.reparse_expr, pathpoints = parse(self.name)
            self.slave_pathpoints = []
            for pp in pathpoints:
                self.slave_pathpoints.append(self.device.get_pathpoint(pp, storage_level))

    def get_archive(self,
                    starting_at: int,
                    stopping_at: tp.Optional[int] = None) -> tp.Iterator[
            tp.Tuple[int, ValueOrExcept]]:
        """
        Get archive readings.

        This will be readed entirely from the device's data, the server will not be queried

        :param starting_at: timestamp of start, in milliseconds
        :param stopping_at: timestamp of end, in milliseconds, or None for the end of the park
        :return: an iterator of tuple (timestamp in milliseconds,
                                       pathpoint value or exception instance)
        """
        yield from self.device.pp_database.get_archive_data(self.name, starting_at, stopping_at)

    @must_have_device
    def set_new_value(self, timestamp: Number, value: ValueOrExcept) -> None:
        """
        May be called asynchronously by user threads to asynchronously update a pathpoint

        :param timestamp: new timestamp
        :param value: new value
        """
        self.device.pp_database.on_new_data(self.name, timestamp, value)
        if self.device.getter is not None:
            self.device.getter.data_to_update.notify()
        self.current_timestamp = timestamp
        self.current_value = value

    @abstractmethod
    def on_read(self, advise: AdviseLevel) -> Future:
        """
        Called when there's a request to read this pathpoint.

        This is called from a separate thread spawned by SMOKDevice.

        The future should raise OperationFailedError when the read fails.

        .. note:: :attr:`current_timestamp` and :attr:`current_value` will be automatically
                  updated, so there's no need for the future to do that.

        :param advise: advise level of this read operation
        :returns: a Future that returns the value of this pathpoint or raises OperationFailedError.
            This Future can also return None, if the value will be set later via
            :meth:`~smokclient.pathpoint.Pathpoint.set_new_value`
        """

    @abstractmethod
    def on_write(self, value: PathpointValueType, advise: AdviseLevel) -> Future:
        """
        Called when there's a request to write this pathpoint with a particular value

        This is called from a separate thread spawned by SMOKDevice

        The future should raise OperationFailedError when the write fails.

        :param value: value to be written
        :param advise: advise level of this read operation
        :returns: a Future that completes successfully if written correctly or excepts if failed
            (you should raise OperationFailedError).
        """

    def on_new_storage_level(self, new_storage_level: StorageLevel) -> None:
        """
        Called when this pathpoint's storage level is updated.

        This is usually invoked by syncing the pathpoints with the server.

        This should complete ASAP, as this is called by a thread that is responsible
        for communication with the server.

        :param new_storage_level: new storage level for this pathpoint
        """
        self.storage_level = new_storage_level

    @must_have_device
    def get(self) -> tp.Tuple[Number, PathpointValueType]:
        """
        Return the current pathpoint value

        :return: a tuple of (last timestamp, when the operation has failed)
        :raises OperationFailedError: when pathpoint's read has failed
        """
        if self.current_value is None:
            ts, v = self.device.pp_database.get_current_value(self.name)  # raises NotReadedError
            self.current_timestamp = ts
            self.current_value = v

        if isinstance(self.current_value, OperationFailedError):
            raise self.current_value
        else:
            return self.current_timestamp, self.current_value

    def read(self, advise_level: AdviseLevel = AdviseLevel.ADVISE) -> Section:
        """
        Return an order that reads this pathpoint

        Dispatch them like this:

        >>> my_sd.execute(pp.read(2))

        :param advise_level: required advise level
        :return: a Section, whose execution will refresh the value in the pathpoint
        """
        return Section([ReadOrder(self.name, advise_level)])

    def write(self, value: PathpointValueType, advise_level: AdviseLevel = AdviseLevel.ADVISE,
              stale_after: tp.Optional[float] = None) -> Section:
        """
        Return an order, whose execution will put target value in target pathpoint.

        Dispatch them like this:

        >>> my_sd.execute(pp.write(2))

        :param value: value to write
        :param advise_level: advise level with which to write
        :param stale_after: timestamp, that if given, will prevent the write from being executed
            past it
        :return: a Section, whose execution will put the target value in the pathpoint
        """
        return Section([WriteOrder(self.name, value, advise_level, stale_after)])
