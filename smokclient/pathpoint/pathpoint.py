import typing as tp
from abc import ABCMeta, abstractmethod
from concurrent.futures import Future

PathpointValueType = tp.Union[int, float, str]


class Pathpoint(metaclass=ABCMeta):
    """
    Base class for an user-defined pathpoint.
    """

    @abstractmethod
    def on_read(self) -> Future:
        """
        Called when there's a request to read this pathpoint.

        This is called from a separate thread spawned by SMOKDevice

        :returns: a Future that returns the value of this pathpoint
        """

    @abstractmethod
    def on_write(self, value: PathpointValueType) -> Future:
        """
        Called when there's a request to write this pathpoint with a particular value

        This is called from a separate thread spawned by SMOKDevice

        :returns: a Future that completes successfully if written correctly or excepts if failed
            (any exception will do).
        """

