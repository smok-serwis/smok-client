import typing as tp
from abc import ABCMeta, abstractmethod


class BaseMetadataDatabase(metaclass=ABCMeta):
    """
    Base class for metadata databases
    """

    @abstractmethod
    def put_plain(self, key: str, value: str, timestamp: tp.Optional[float] = None) -> None:
        """
        A plain value was just written.

        :param key: key of the write
        :param value: value of the write
        :param timestamp: timestamp of the write, default is current
        """

    @abstractmethod
    def get_plain(self, key: str) -> str:
        """
        Return a value for given plain key

        :param key: key to give a value for
        :raises KeyError: key not found, ask the server
        """

    @abstractmethod
    def update_plain(self, key: str, value: str, timestamp: float) -> None:
        """
        On an update plain request from the server

        :param key: key of the key
        :param value: value of the key
        :param timestamp: timestamp at which time it was last written
        """

    @abstractmethod
    def delete_plain(self, key: str) -> None:
        """
        Delete a particular key for plain database

        No-op on key not being in the database.

        :param key: key to delete
        """

    @abstractmethod
    def get_all_plain(self) -> tp.Iterator[tp.Tuple[str, str, float]]:
        """
        Get all plain keys in the database

        :return: an iterator of tuple(key, value, timestamp of the write)
        """
