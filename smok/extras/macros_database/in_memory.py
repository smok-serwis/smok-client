import copy
import logging
import typing as tp

from satella.coding import silence_excs, for_argument
from satella.coding.predicates import x
from satella.coding.sequences import choose

from smok.extras.macros_database.base import BaseMacroDatabase
from smok.macro import Macro

logger = logging.getLogger(__name__)


class InMemoryMacroDatabase(BaseMacroDatabase):
    def __init__(self):
        self.macros_to_execute = []  # type: tp.List[Macro]
        self.executions_to_sync = []  # type: tp.List[tp.Tuple[str, int]]

    def set_macros(self, macros: tp.List[Macro]) -> None:
        self.macros_to_execute = macros

    def get_macros(self) -> tp.List[Macro]:
        return self.macros_to_execute

    @silence_excs(ValueError)
    def notify_macro_executed(self, macro_id: str, timestamp: int) -> None:
        macro = choose(x.macro_id == macro_id, self.macros_to_execute)  # throws ValueError
        self.executions_to_sync.append((macro_id, timestamp))
        if not macro:
            self.macros_to_execute.remove(macro)

    @for_argument(returns=copy.copy)
    def get_done_macros(self) -> tp.Iterator[tp.Tuple[str, int]]:
        return self.executions_to_sync

    @silence_excs(ValueError)
    def notify_macro_synced(self, macro_id: str, timestamp: int) -> None:
        self.executions_to_sync.remove((macro_id, timestamp))

    def checkpoint(self) -> None:
        pass
