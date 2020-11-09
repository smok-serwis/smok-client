import logging
import time
import collections

from satella.coding import silence_excs
from satella.coding.concurrent import PeekableQueue
from satella.coding.decorators import retry
from satella.coding.structures import OmniHashableMixin, ReprableMixin

from smokclient.exceptions import ResponseError
from smokclient.pathpoint.orders import Section, WriteOrder, AdviseLevel
from smokclient.pathpoint.typing import PathpointValueType
import typing as tp

logger = logging.getLogger(__name__)


class Macro(OmniHashableMixin, ReprableMixin):
    _HASH_FIELDS_TO_USE = ('macro_id', )
    _REPR_FIELDS = ('macro_id', 'commands', 'occurrences_not_done')
    __slots__ = ('macro_id', 'commands', 'occurrences_not_done')

    def __init__(self, macro_id: str, commands: tp.Dict[str, PathpointValueType],
                 occurrences_not_done: tp.List[float]):
        self.macro_id = macro_id
        self.commands = commands
        self.occurrences_not_done = collections.deque(sorted(occurrences_not_done))

    def __bool__(self) -> bool:
        return bool(self.occurrences_not_done)

    @silence_excs(IndexError, returns=False)
    def should_execute(self) -> bool:
        return time.time() > self.occurrences_not_done[0]

    @retry(3, exc_classes=ResponseError)
    def mark_as_complete(self, ts: int, device: 'SMOKDevice') -> None:
        device.api.post('/v1/device/macros/%s/%s' % (self.macro_id, ts))

    def execute(self, device: 'SMOKDevice', order_queue: PeekableQueue) -> None:
        logger.warning(f'Executing')
        while self.should_execute():
            sec = Section()
            for pathpoint_name, pathpoint_value in self.commands.items():
                sec += WriteOrder(pathpoint_name, pathpoint_value, AdviseLevel.FORCE)
            order_queue.put(sec)

            ts = self.occurrences_not_done.popleft()
            self.mark_as_complete(ts, device)


macro_cache = {}        # type: tp.Dict[str, Macro]


def get_macro(macro_id: str, commands, occurrences):
    global macro_cache

    if not macro_id in macro_cache:
        macro_cache[macro_id] = Macro(macro_id, commands, occurrences)
        logger.warning(f'Registered new macro {macro_cache[macro_id]}')

    return macro_cache[macro_id]


def macro_parameters_from_json(dct: dict) -> tp.Tuple[str,
                                                      tp.Dict[str, PathpointValueType],
                                                      tp.List[float]]:
    macro_id = dct['macro_id']
    commands = {}
    for command in dct['commands']:
        commands[command['path']] = command['value']
    occurrences = []
    for occ in dct['occurrences']:
        if not occ['completed']:
            occurrences.append(occ['timestamp'])

    return macro_id, commands, occurrences


def clean_cache():
    for macro_id in list(macro_cache.keys()):
        if not macro_cache[macro_id]:
            del macro_cache[macro_id]
