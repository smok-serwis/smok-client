import typing as tp
from abc import ABCMeta, abstractmethod

from smok.predicate.event import Event


class BaseEventSynchronization(metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def get_events(self) -> tp.List[Event]:
        """
        :return: a list of events to synchronize
        """

    @abstractmethod
    def acknowledge(self, *uuids: str) -> None:
        """
        Called by the communicator, when sync succeeds

        :param uuids: UUIDs assigned to events"""

    @abstractmethod
    def negative_acknowledge(self) -> None:
        """Called by the communicator, when sync fails"""


class BaseEventDatabase(metaclass=ABCMeta):

    @abstractmethod
    def checkpoint(self) -> None:
        """
        Called by the communicator thread, once every about 60 seconds.
        May be called much more often, it's the function responsibility to throttle.
        """

    @abstractmethod
    def get_open_events(self) -> tp.Iterator[Event]:
        """
        :return: an iterator with all open events
        """

    @abstractmethod
    def get_all_events(self) -> tp.Iterator[Event]:
        """
        :return: all events kept in the database
        """

    @abstractmethod
    def close_event(self, event: Event) -> None:
        """
        Close provided event

        :param event: event to close
        """

    @abstractmethod
    def add_event(self, event: Event) -> None:
        """
        Register a new event in the database.

        Can be called by any thread.

        :param event: event to register
        """

    @abstractmethod
    def get_events_to_sync(self) -> tp.Optional[BaseEventSynchronization]:
        """
        At most a single instance of BaseEventSynchronization will be alive at a time.

        :return: object to sync, or None if there's nothing to sync.
        """

    @abstractmethod
    def set_cache(self, predicate_id: str, cache) -> None:
        """
        Store predicate's internal data. Do it in a way that will survive restarts.
        """

    @abstractmethod
    def get_cache(self, predicate_id: str) -> tp.Any:
        """
        Return predicate's internal data

        :raises KeyError: predicate internal data not found
        """

    @abstractmethod
    def on_predicate_deleted(self, predicate_id: str) -> None:
        """
        Called when a predicate is deleted.

        Called by communicator thread.

        :param predicate_id: ID of the predicate that was deleted
        """
