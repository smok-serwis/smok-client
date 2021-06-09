import typing as tp
from abc import abstractmethod, ABCMeta


class SyncError(Exception):
    """
    An error has happened during the sync
    """
    def __init__(self, is_no_link: bool = True):
        self._is_no_link = is_no_link

    def is_no_link(self):
        return self._is_no_link


class BaseSyncWorker(metaclass=ABCMeta):
    """
    Base class for synchronizing archives and logs
    """
    def __init__(self, device: 'SMOKDevice'):
        self.device = device

    @abstractmethod
    def sync_logs(self, data: tp.List[dict]):
        ...

    @abstractmethod
    def close(self):
        ...

