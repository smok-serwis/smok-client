import os
import pickle
import typing as tp

from satella.coding import silence_excs, wraps

from smok.extras.macros_database.in_memory import InMemoryMacroDatabase
from smok.macro import Macro


def always_sync(fun):
    @wraps(fun)
    def inner(self, *args, **kwargs):
        try:
            return fun(self, *args, **kwargs)
        finally:
            getattr(self, '_PicklingMacroDatabase__sync')()

    return inner


class PicklingMacroDatabase(InMemoryMacroDatabase):
    """
    An example persistent macro database

    :param path: path to pickle file
    """

    def __init__(self, path):
        super().__init__()
        self.__path = path

        if os.path.exists(self.__path):
            with open(self.__path, 'rb') as f_in, silence_excs(pickle.PickleError):
                self.macros_to_execute, self.executions_to_sync = pickle.load(f_in)

    def __sync(self):
        with open(self.__path, 'wb') as f_out:
            pickle.dump((self.macros_to_execute, self.executions_to_sync), f_out,
                        pickle.HIGHEST_PROTOCOL)

    @always_sync
    def set_macros(self, macros: tp.List[Macro]) -> None:
        super().set_macros(macros)

    @always_sync
    def get_macros(self) -> tp.List[Macro]:
        return super().get_macros()

    @always_sync
    def notify_macro_executed(self, macro_id: str, timestamp: int) -> None:
        return super().notify_macro_executed(macro_id, timestamp)

    def get_done_macros(self) -> tp.Iterator[tp.Tuple[str, int]]:
        return super().get_done_macros()

    @always_sync
    def notify_macro_synced(self, macro_id: str, timestamp: int) -> None:
        return super().notify_macro_synced(macro_id, timestamp)
