import os
import pickle
import typing as tp
import weakref

from satella.coding import Monitor, silence_excs
from satella.time import time_as_int

from .base import BaseEventDatabase, BaseEventSynchronization
from ...predicate.event import Event


class InMemoryEventSynchronization(BaseEventSynchronization):

    __slots__ = ('event_db', 'events', )

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

    @Monitor.synchronized
    def get_open_events(self) -> tp.Iterator[Event]:
        for event in self.events:
            if not event.is_closed():
                yield event

    @Monitor.synchronized
    def close_event(self, event: Event) -> None:
        self.events_to_sync.append(event)

    @Monitor.synchronized
    def get_data_to_sync(self) -> tp.Optional[BaseEventSynchronization]:
        if not self.events_to_sync:
            return None
        else:
            return InMemoryEventSynchronization(self, self.events_to_sync)

    @Monitor.synchronized
    def add_event(self, event: Event) -> None:
        self.events.append(event)
        self.events_to_sync.append(event)

    def __init__(self, path: str):
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

    def checkpoint(self) -> None:
        pass

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
