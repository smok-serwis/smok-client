import collections
import logging
import pickle
import time
import typing as tp
import weakref

from satella.coding import silence_excs
from satella.coding.structures import OmniHashableMixin, ReprableMixin

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

    def __getstate__(self):
        return {'macro_id': self.macro_id,
                'commands': self.commands,
                'occurrences_not_done': self.occurrences_not_done}

    def __setstate__(self, state):
        self.macro_id = state['macro_id']
        self.commands = state['commands']
        self.occurrences_not_done = state['occurrences_not_done']

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
    def from_pickle(cls, y: bytes, device: 'SMOKDevice') -> 'Macro':
        macro = pickle.loads(y)
        macro.device = weakref.proxy(device)
        return macro

    def __bool__(self) -> bool:
        return bool(self.occurrences_not_done)

    @silence_excs(IndexError, returns=False)
    def should_execute(self) -> bool:
        return time.time() > self.occurrences_not_done[0]

    def execute(self) -> None:
        logger.debug(f'Executing macro %s with commands %s', self.macro_id, self.commands)
        while self.should_execute():
            ts = self.occurrences_not_done.popleft()
            sec = Section([WriteOrder(pathpoint_name, pathpoint_value, AdviseLevel.FORCE)
                           for pathpoint_name, pathpoint_value in self.commands.items()])
            self.device.execute(sec)
            self.device.macros_database.notify_macro_executed(self.macro_id, ts)

