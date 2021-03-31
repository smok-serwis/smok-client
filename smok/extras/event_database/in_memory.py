import os
import pickle
import time
import typing as tp
import weakref

from satella.coding import Monitor, silence_excs
from satella.time import parse_time_string

from .base import BaseEventDatabase, BaseEventSynchronization
from ...predicate.event import Event


class InMemoryEventSynchronization(BaseEventSynchronization):
    __slots__ = ('event_db', 'events',)

    def __init__(self, event_db: 'InMemoryEventDatabase', events: tp.List[Event]):
        self.event_db = weakref.proxy(event_db)
        self.events = events

    def get_events(self) -> tp.List[Event]:
        return self.events

    def acknowledge(self, *uuids: str) -> None:
        for event, uuid in zip(self.events, uuids):
            if event.uuid is None:
                event.uuid = uuid

            if event.is_closed():
                with Monitor.acquire(self.event_db), silence_excs(ValueError):
                    self.events.remove(event)

    def negative_acknowledge(self) -> None:
        pass


class InMemoryEventDatabase(BaseEventDatabase, Monitor):
    """
    :param path: path to a DB file with pickled events
    :param keep_in_memory_for: amount of time to keep events for
    """

    @Monitor.synchronized
    def get_all_events(self) -> tp.Iterator[Event]:
        return iter(list(self.events))

    @Monitor.synchronized
    def get_open_events(self) -> tp.Iterator[Event]:
        for event in self.events:
            if not event.is_closed():
                yield event

    @Monitor.synchronized
    def close_event(self, event: Event) -> None:
        self.events_to_sync.append(event)

    @Monitor.synchronized
    def get_events_to_sync(self) -> tp.Optional[BaseEventSynchronization]:
        if not self.events_to_sync:
            return None
        else:
            return InMemoryEventSynchronization(self, self.events_to_sync)

    @Monitor.synchronized
    def add_event(self, event: Event) -> None:
        self.events.append(event)
        self.events_to_sync.append(event)

    def __init__(self, path: str, keep_in_memory_for: tp.Union[str, int] = '30d'):
        self.events = []
        self.path = path
        self.internal_data = {}
        self.events_to_sync = []
        Monitor.__init__(self)
        if os.path.exists(self.path):
            with open(self.path, 'rb') as f_in:
                try:
                    self.internal_data = pickle.load(f_in)
                except pickle.PickleError:
                    pass
        self.keep_in_memory_for = parse_time_string(keep_in_memory_for)

    @Monitor.synchronized
    def checkpoint(self) -> None:
        for i in range(len(self.events)):
            if self.events[i].is_closed():
                if time.time() - self.events.started_on > self.keep_in_memory_for:
                    del self.events[i]
                    return

    def set_cache(self, predicate_id: str, cache) -> None:
        self.internal_data[predicate_id] = cache
        self.sync()

    def get_cache(self, predicate_id: str) -> tp.Any:
        return self.internal_data[predicate_id]

    def sync(self):
        with open(self.path, 'wb') as f_out:
            pickle.dump(self.internal_data, f_out, pickle.HIGHEST_PROTOCOL)

    @silence_excs(KeyError)
    def on_predicate_deleted(self, predicate_id: str) -> None:
        del self.internal_data[predicate_id]
        self.sync()
