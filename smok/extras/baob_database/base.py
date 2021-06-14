import logging
import typing as tp
from abc import ABCMeta, abstractmethod

logger = logging.getLogger(__name__)


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

    def check_consistency(self) -> None:
        """
        Check that for all keys that are returned by `get_all_keys` version can be
        obtained via `get_baob_version`.

        If not, delete such a key and log an ERROR.

        Called by constructor of :class:`~smok.client.SMOKDevice`
        """
        for key in self.get_all_keys():
            try:
                self.get_baob_version(key)
            except KeyError:
                logger.error(
                    'Key %s mentioned in all keys but cannot get a version for it, deleting', key)
                self.delete_baob(key)
