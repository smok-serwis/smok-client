import collections
import logging
import pickle
import time
import typing as tp
import weakref

from satella.coding import silence_excs, DictDeleter
from satella.coding.concurrent import PeekableQueue
from satella.coding.decorators import retry
from satella.coding.structures import OmniHashableMixin, ReprableMixin

from smok.exceptions import ResponseError
from smok.pathpoint.orders import Section, WriteOrder, AdviseLevel
from smok.pathpoint.typing import PathpointValueType

logger = logging.getLogger(__name__)


class Macro(OmniHashableMixin, ReprableMixin):
    _HASH_FIELDS_TO_USE = ('macro_id',)
    _REPR_FIELDS = ('macro_id', 'commands', 'occurrences_not_done')
    __slots__ = ('macro_id', 'commands', 'occurrences_not_done', 'device')

    @classmethod
    def from_json(cls, device: 'SMOKDevice', dct: dict) -> 'Macro':
        macro_id = dct['macro_id']
        commands = {}
        for command in dct['commands']:
            commands[command['path']] = command['value']
        occurrences = []
        for occ in dct['occurrences']:
            if not occ['completed']:
                occurrences.append(occ['timestamp'])

        return Macro(device, macro_id, commands, occurrences)

    def __init__(self, device: 'SMOKDevice', macro_id: str,
                 commands: tp.Dict[str, PathpointValueType],
                 occurrences_not_done: tp.List[float]):
        self.device = weakref.proxy(device)
        self.macro_id = macro_id
        self.commands = commands
        self.occurrences_not_done = collections.deque(sorted(occurrences_not_done))

    def to_pickle(self) -> bytes:
        """
        :return: self, pickled
        """
        return pickle.dumps(self, pickle.HIGHEST_PROTOCOL)

    @classmethod
    def from_pickle(cls, y: bytes) -> 'Macro':
        return pickle.loads(y)

    def __bool__(self) -> bool:
        return bool(self.occurrences_not_done)

    @silence_excs(IndexError, returns=False)
    def should_execute(self) -> bool:
        return time.time() > self.occurrences_not_done[0]

    def execute(self) -> None:
        logger.warning(f'Executing macro {self.macro_id} with commands {self.commands}')
        while self.should_execute():
            ts = self.occurrences_not_done.popleft()
            sec = Section([WriteOrder(pathpoint_name, pathpoint_value, AdviseLevel.FORCE)
                           for pathpoint_name, pathpoint_value in self.commands.items()])
            self.device.execute(sec)
            self.device.macros_database.notify_macro_executed(self.macro_id, ts)

