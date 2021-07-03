import typing as tp
from abc import abstractmethod, ABCMeta


class SyncError(Exception):
    """
    An error has happened during the sync
    """

    def __init__(self, is_no_link: bool = True, is_clients_fault: bool = False):
        self._is_no_link = is_no_link
        self._is_clients_fault = is_clients_fault

    def is_no_link(self):
        return self._is_no_link

    def is_clients_fault(self):
        return self._is_clients_fault


class BaseSyncWorker(metaclass=ABCMeta):
    """
    Base class for synchronizing archives and logs

    :ivar has_async_orders: (bool) whether this can asynchronously issue orders. If it can,
        you need to take care to inject received orders appropriately.
    """

    def __init__(self, device: 'SMOKDevice', has_async_orders: bool):
        self.device = device
        self.has_async_orders = has_async_orders

    @abstractmethod
    def sync_logs(self, data: tp.List[dict]):
        """
        :raises SyncError: on failure
        """

    @abstractmethod
    def close(self):
        ...

    @abstractmethod
    def sync_pathpoints(self, data: tp.List[dict]):
        """
        Synchronize the pathpoint data

        :raises SyncError: on failure
        """
