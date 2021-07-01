import logging
import time
import typing as tp
import warnings
import weakref
from concurrent.futures import Future

from satella.coding import wraps
from satella.coding.structures import ReprableMixin, OmniHashableMixin
from satella.coding.typing import Number
from satella.instrumentation import Traceback

from .orders import AdviseLevel, Section, ReadOrder, WriteOrder
from .typing import PathpointValueType, ValueOrExcept
from ..basics import StorageLevel
from ..exceptions import OperationFailedError, InstanceNotReady, NotReadedError

logger = logging.getLogger(__name__)


def must_have_device(fun):
    @wraps(fun)
    def inner(self, *args, **kwargs):
        if not self.device:
            raise InstanceNotReady('You need to attach this pathpoint to a device first')
        return fun(self, *args, **kwargs)

    return inner


class Pathpoint(ReprableMixin, OmniHashableMixin):
    """
    Base class for an user-defined pathpoint.

    Note that pathpoint is registered in the device as part of it's creation.

    :param device: device that this pathpoint should be attached to. None is also a valid option.
    :param name: pathpoint name.
    :param storage_level: storage level for this pathpoint
    :param callable_on_change: a callable to be called each time this pathpoint changes value,
        with this pathpoint as it's sole argument. Should this callable return an exception, it will
        be logged as an ERROR along with it's traceback.
    :param read_no_often_than: this pathpoint should be readed at fastest each this seconds.
        Leave it at None (default) to disable this mechanism.

    :ivar name: pathpoint name
    :ivar storage_level: pathpoint's storage level
    :ivar current_timestamp: a timestamp in seconds of the last read
    :ivar current_value: last readed value or an exception instance
    :ivar device: a weak reference to the device
    """
    _HASH_FIELDS_TO_USE = 'name',
    _REPR_FIELDS = 'name', 'storage_level'
    __slots__ = 'name', 'storage_level', 'current_value', 'current_timestamp', 'device', \
                'callable_on_change', 'read_no_often_than', 'last_read'

    def __init__(self, device: tp.Optional['SMOKDevice'], name: str,
                 storage_level: StorageLevel = StorageLevel.TREND,
                 callable_on_change: tp.Optional[tp.Callable[['Pathpoint'], None]] = None,
                 read_no_often_than: tp.Optional[float] = None):
        self.device = weakref.proxy(device)
        self.name = name
        self.read_no_often_than = read_no_often_than
        self.last_read = 0
        self.callable_on_change = callable_on_change
        self.storage_level = storage_level
        # Try to load
        try:
            self.current_timestamp, self.current_value = device.pp_database.get_current_value(name)
        except NotReadedError:
            self.current_timestamp = None
            self.current_value = None
        except OperationFailedError as e:
            self.current_timestamp = e.timestamp
            self.current_value = e

        # noinspection PyProtectedMember
        if device is not None:
            device.register_pathpoint(self)

    def can_read(self) -> bool:
        """
        Called by the executor before a ReadOrder is processed to determine whether this
        pathpoint can be read.

        :return: Can this pathpoint be read?
        """
        if self.read_no_often_than is not None:
            return time.monotonic() - self.last_read > self.read_no_often_than
        return True

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
    def set_new_value(self, *args) -> None:
        """
        May be called asynchronously by user threads to asynchronously update a pathpoint.

        This is also called by the executor thread upon reading a new piece of data.

        You can use it in one of two ways:

        >>> pp.set_new_value(timestamp, value)

        or:

        >>> pp.set_new_value(OperationFailedError(...))

        :param timestamp: new timestamp
        :param value: new value
        """
        if len(args) == 1:
            value, = args
            timestamp = value.timestamp
        else:
            timestamp, value = args
        if self.current_timestamp is not None:
            if self.current_timestamp >= timestamp:
                warnings.warn(
                    'Given lower or equal timestamp (%s) than current one (%s), ignoring' % (
                        timestamp, self.current_timestamp), UserWarning)
                return
        self.device.pp_database.on_new_data(self.name, timestamp, value)
        if self.device.getter is not None:
            self.device.getter.data_to_update.notify()
        self.current_timestamp = timestamp
        self.current_value = value
        if self.callable_on_change is not None:
            try:
                self.callable_on_change(self)
            except Exception as e:
                logger.error('Callback on change for %s failed with %s, ignoring', self.name,
                             Traceback().pretty_format(), exc_info=e)
        self.last_read = time.monotonic()

    def on_read(self, advise: AdviseLevel) -> tp.Optional[tp.Union[PathpointValueType, Future]]:
        """
        Called when there's a request to read this pathpoint.

        This is called from a separate thread spawned by SMOKDevice.

        Note that :meth:`~smok.pathpoint.Pathpoint.can_read` will be checked for before this is
        called.

        This may return a Future, that results in the value readed, or should raise
        OperationFailedError when the read fails, or should directly return the value,
        or should directly raise the exception.

        .. note:: :attr:`current_timestamp` and :attr:`current_value` will be automatically
                  updated, so there's no need for the future to do that.

        :param advise: advise level of this read operation
        :returns: a Future that returns the value of this pathpoint or raises OperationFailedError.
            This Future can also return None, if the value will be set later via
            :meth:`~smokclient.pathpoint.Pathpoint.set_new_value`
        :raises OperationFailedError: operation failed
        """

    def on_write(self, value: PathpointValueType, advise: AdviseLevel) -> tp.Optional[Future]:
        """
        Called when there's a request to write this pathpoint with a particular value

        This is called from a separate thread spawned by SMOKDevice

        The future should raise OperationFailedError when the write fails.
        This can return None if the write won't be executed and should be treated as successful.

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
        :raises NotReadedError: pathpoint not yet readed
        """
        if self.current_value is None:
            raise NotReadedError()

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
