import typing as tp

from .base import BaseEventDatabase, BaseEventSynchronization
from ...predicate import Event


class NullEventDatabase(BaseEventDatabase):
    """
    For these use cases where you don't use events at all.
    """

    def on_predicate_deleted(self, predicate_id: str) -> None:
        pass

    def get_cache(self, predicate_id: str) -> tp.Any:
        raise KeyError()

    def set_cache(self, predicate_id: str, cache) -> None:
        pass

    def get_events_to_sync(self) -> tp.Optional[BaseEventSynchronization]:
        return None

    def add_event(self, event: Event) -> None:
        pass

    def close_event(self, event: Event) -> None:
        pass

    def get_all_events(self) -> tp.Iterator[Event]:
        return iter([])

    def get_open_events(self) -> tp.Iterator[Event]:
        return iter([])

    def checkpoint(self) -> None:
        pass
