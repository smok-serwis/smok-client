import typing as tp
from abc import ABCMeta, abstractmethod

from smok.macro import Macro


class BaseMacroDatabase(metaclass=ABCMeta):

    @abstractmethod
    def get_done_macros(self) -> tp.Iterator[tp.Tuple[str, int]]:
        """
        Get a list of macros that were done, but the server wasn't told about that yet.

        Called by communicator thread

        :return: an iterator of a tuple (macro_id, executed timestamps)
        """

    @abstractmethod
    def notify_macro_synced(self, macro_id: str, timestamp: int) -> None:
        """
        Notify the DB that server has received notification about executing given macro.

        Called by communicator thread
        """

    @abstractmethod
    def notify_macro_executed(self, macro_id: str, timestamp: int) -> None:
        """
        Notify the DB that the device has executed a given macro.

        This should update the database's macro definition as well.

        Called by archive & macro thread
        """

    @abstractmethod
    def set_macros(self, macros: tp.List[Macro]) -> None:
        """
        Set current list of macros to execute (have been not yet executed)

        :param macros: list of macro to execute
        """

    @abstractmethod
    def get_macros(self) -> tp.List[Macro]:
        """
        Get a list of macros to execute
        """

    @abstractmethod
    def checkpoint(self) -> None:
        """
        Called about each 60 seconds by communicator thread
        """
