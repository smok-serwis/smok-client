import typing as tp
from abc import abstractmethod, ABCMeta


class BaseArchivesDatabase(metaclass=ABCMeta):
    """
    A base class for databases with archiving instructions.
    """

    @abstractmethod
    def get_archiving_instructions(self) -> tp.Dict[int, tp.List[str]]:
        """
        Return currently stored archiving instructions, or an empty dict if none available.

        Called by `ArchivingAndMacroThread`

        :return: a dictionary of (archiving_interval::int => list of pathpoints to archive)
        """

    @abstractmethod
    def on_archiving_data_sync(self, new_data: tp.Dict[int, tp.List[str]]) -> None:
        """
        Called on new archiving data instructions.

        Called by `ArchivingAndMacroThread`

        :param new_data: a dictionary of (archiving_interval::int => list of pathpoints to archive)
        """
