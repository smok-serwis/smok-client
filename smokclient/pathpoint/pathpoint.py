from abc import ABCMeta, abstractmethod
from concurrent.futures import Future

from satella.coding.structures import ReprableMixin

from .orders import AdviseLevel
from .typing import PathpointValueType
from ..basics import StorageLevel


class Pathpoint(ReprableMixin, metaclass=ABCMeta):
    """
    Base class for an user-defined pathpoint.

    :param name: pathpoint name.
    :param storage_level: storage level for this pathpoint

    :ivar name: pathpoint name
    :ivar storage_level: pathpoint's storage level
    """
    _REPR_FIELDS = ('name', 'storage_level')
    __slots__ = ('name', 'storage_level')

    def __init__(self, name: str, storage_level: StorageLevel = StorageLevel.TREND):
        self.name = name
        self.storage_level = storage_level

    @abstractmethod
    def on_read(self, advise: AdviseLevel) -> Future:
        """
        Called when there's a request to read this pathpoint.

        This is called from a separate thread spawned by SMOKDevice.

        The future should raise OperationFailedError when the read fails.

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

