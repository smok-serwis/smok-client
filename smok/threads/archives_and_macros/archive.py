from __future__ import annotations
import time
import typing as tp

from satella.coding import for_argument
from satella.coding.structures import OmniHashableMixin, ReprableMixin
from satella.coding.typing import Number

from smok.basics import StorageLevel
from smok.exceptions import OperationFailedError
from smok.pathpoint import Pathpoint
from smok.pathpoint.orders import Section


class ArchivingEntry(OmniHashableMixin, ReprableMixin):
    _REPR_FIELDS = 'pathpoint', 'interval'
    _HASH_FIELDS_TO_USE = 'pathpoint',
    __slots__ = 'pathpoint', 'interval'

    @staticmethod
    def provide(client, pp_name: str, interval: Number) -> ArchivingEntry:
        return ArchivingEntry(client.get_pathpoint(pp_name, StorageLevel.PERMANENT), interval)

    def __init__(self, pathpoint: Pathpoint, interval: Number):
        self.pathpoint = pathpoint
        self.interval = interval

    def should_update(self) -> bool:
        try:
            ts = self.pathpoint.get()[0]
        except OperationFailedError:
            return True
        return time.time() - ts >= self.interval

    def update(self) -> Section:
        if self.should_update():
            return self.pathpoint.read()
        else:
            return Section([])


@for_argument(returns=set)
def archiving_entries_from_json(client: 'SMOKDevice', y: tp.List[dict]) -> tp.Set[ArchivingEntry]:
    for entry in y:
        interval = entry['interval']
        for pp in entry['pathpoints']:
            yield ArchivingEntry.provide(client, pp, interval)


def archiving_dict_from_json(y: tp.List[dict]) -> tp.Dict[int, tp.List[str]]:
    result = {}
    for entry in y:
        interval = entry['interval']
        result[interval] = entry['pathpoints']
    return result
