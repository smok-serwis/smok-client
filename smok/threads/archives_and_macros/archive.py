import time
import typing as tp

from satella.coding import for_argument
from satella.coding.structures import OmniHashableMixin, ReprableMixin
from satella.coding.typing import Number

from smok.pathpoint.orders import Section, ReadOrder, AdviseLevel


class ArchivingEntry(OmniHashableMixin, ReprableMixin):
    _REPR_FIELDS = ('pathpoint_name', 'interval')
    _HASH_FIELDS_TO_USE = ('pathpoint_name',)
    __slots__ = ('pathpoint_name', 'interval', 'last_updated')

    def __init__(self, pathpoint_name: str, interval: Number):
        self.pathpoint_name = pathpoint_name
        self.interval = interval
        self.last_updated = 0

    def should_update(self) -> bool:
        return time.time() - self.last_updated > self.interval

    def update(self) -> Section:
        self.last_updated = time.time()
        return Section([ReadOrder(self.pathpoint_name, AdviseLevel.ADVISE)])


@for_argument(returns=set)
def archiving_entries_from_json(y: tp.List[dict]) -> tp.Set[ArchivingEntry]:
    for entry in y:
        interval = entry['interval']
        for pp in entry['pathpoints']:
            yield ArchivingEntry(pp, interval)


def archiving_dict_from_json(y: tp.List[dict]) -> tp.Dict[int, tp.List[str]]:
    result = {}
    for entry in y:
        interval = entry['interval']
        result[entry['interval']] = entry['pathpoints']
    return result
