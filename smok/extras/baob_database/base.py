import typing as tp
from abc import ABCMeta, abstractmethod


class BAOBDigest:
    """
    A descriptor of a BAOB

    :ivar key: key of this BAOB (str)
    :ivar version: version of this BAOB (int)
    """

    __slots__ = ('key', 'version')

    def __init__(self, key: str, version: int):
        self.key = key
        self.version = version


class BaseBAOBDatabase(metaclass=ABCMeta):
    @abstractmethod
    def get_baob_value(self, key: str) -> bytes:
        """
        Return a value of a particular BAOB

        :raises KeyError: BAOB does not exist
        """

    @abstractmethod
    def delete_baob(self, key: str) -> None:
        """
        Delete particular BAOB

        :raises KeyError: BAOB does not exist
        """

    @abstractmethod
    def get_baob_version(self, key: str) -> int:
        """
        Return a version of particular BAOB

        :raises KeyError: BAOB does not exist
        """

    @abstractmethod
    def get_all_keys(self) -> tp.Iterator[str]:
        """
        Stream all keys of BAOBs stored locally
        """

    @abstractmethod
    def set_baob_value(self, key: str, data: bytes, version: int):
        """
        Store a particular version of a BAOB within the database
        """
