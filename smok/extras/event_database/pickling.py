import os
import pickle
import typing as tp

from satella.coding import silence_excs, Monitor

from smok.extras.event_database import InMemoryEventDatabase
from smok.extras.event_database.in_memory import InMemoryEventSynchronization
from smok.predicate import Event


class PicklingEventSynchronization(InMemoryEventSynchronization):

    def acknowledge(self, *uuids: str) -> None:
        super().acknowledge(*uuids)
        self.event_db.dirty = True


class PicklingEventDatabase(InMemoryEventDatabase):
    """
    A simple database that pickles events on disk each
    :meth:`~smokclient.extras.BaseEventSynchronization.checkpoint`

    :param cache_path: path to cache with predicate's data
    :param data_path: path to cache with event data
    """

    def __init__(self, cache_path: str, data_path: str):
        super().__init__(cache_path)
        self.data_path = data_path
        self.dirty = False
        if os.path.exists(self.data_path):
            with open(self.data_path, 'rb') as f_in, silence_excs(pickle.PickleError):
                self.events, self.events_to_sync = pickle.load(f_in)

    def add_event(self, event: Event) -> None:
        super().add_event(event)
        self.dirty = True

    def close_event(self, event: Event) -> None:
        super().close_event(event)
        self.dirty = True

    @Monitor.synchronized
    def get_events_to_sync(self) -> tp.Optional[PicklingEventSynchronization]:
        if not self.events_to_sync:
            return None
        else:
            return PicklingEventSynchronization(self, self.events_to_sync)

    def checkpoint(self):
        evt_len = len(self.events)
        super().checkpoint()
        if evt_len != len(self.events) or self.dirty:
            self.sync_data()

    @Monitor.synchronized
    def sync_data(self):
        with open(self.data_path, 'wb') as f_out:
            pickle.dump((self.events, self.events_to_sync), f_out, pickle.HIGHEST_PROTOCOL)
        self.dirty = False
