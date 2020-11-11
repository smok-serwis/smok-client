import typing as tp
from abc import ABCMeta, abstractmethod
from concurrent.futures import Future

from satella.coding.structures import ReprableMixin
from satella.coding.typing import Number

from .orders import AdviseLevel, Section, ReadOrder, WriteOrder
from .typing import PathpointValueType
from ..basics import StorageLevel
from ..exceptions import OperationFailedError, NotReadedError


class Pathpoint(ReprableMixin, metaclass=ABCMeta):
    """
    Base class for an user-defined pathpoint.

    :param name: pathpoint name.
    :param storage_level: storage level for this pathpoint

    :ivar name: pathpoint name
    :ivar storage_level: pathpoint's storage level
    :ivar current_timestamp: a timestamp in seconds of the last read
    :ivar current_value: last readed value or an exception instance
    """
    _REPR_FIELDS = ('name', 'storage_level')
    __slots__ = ('name', 'storage_level', 'current_value', 'current_timestamp')

    def __init__(self, name: str, storage_level: StorageLevel = StorageLevel.TREND):
        self.name = name
        self.storage_level = storage_level
        self.current_value = None       # type: tp.Union[PathpointValueType, ReadFailedError]
        self.current_timestamp = None   # type: Number

    @abstractmethod
    def on_read(self, advise: AdviseLevel) -> Future:
        """
        Called when there's a request to read this pathpoint.

        This is called from a separate thread spawned by SMOKDevice.

        The future should raise OperationFailedError when the read fails.

        .. note:: :attr:`current_timestamp` and :attr:`current_value` will be automatically updated, so
                  there's no need for the future to do that.

        :param advise: advise level of this read operation
        :returns: a Future that returns the value of this pathpoint or raises OperationFailedError
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

    def get(self) -> tp.Tuple[Number, PathpointValueType]:
        """
        Return the current pathpoint value

        :return: a tuple of (last timestamp, when the operation has failed)
        :raises OperationFailedError: when pathpoint's read has failed
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
