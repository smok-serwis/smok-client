from abc import ABCMeta, abstractmethod
from concurrent.futures import Future

from .orders import AdviseLevel
from .typing import PathpointValueType
from ..basics import StorageLevel


class Pathpoint(metaclass=ABCMeta):
    """
    Base class for an user-defined pathpoint.
    """
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

        :returns: a Future that returns the value of this pathpoint
        """

    @abstractmethod
    def on_write(self, value: PathpointValueType, advise: AdviseLevel) -> Future:
        """
        Called when there's a request to write this pathpoint with a particular value

        This is called from a separate thread spawned by SMOKDevice

        The future should raise OperationFailedError when the write fails.

        :returns: a Future that completes successfully if written correctly or excepts if failed
            (any exception will do).
        """

    def on_new_storage_level(self, new_storage_level: StorageLevel) -> None:
        """
        Called when this pathpoint's storage level is updated.

        This should complete ASAP, as this is called by a thread that is responsible
        for communication with the server.
        """
        self.storage_level = new_storage_level

