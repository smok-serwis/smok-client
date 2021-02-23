import os.path
import pickle
import typing as tp

from satella.coding import Monitor
from satella.coding.typing import Number

from smok.exceptions import NotReadedError, OperationFailedError
from smok.pathpoint import PathpointValueType, ValueOrExcept
from .in_memory import InMemoryPathpointDatabase


class PicklingPathpointDatabase(InMemoryPathpointDatabase):
    """
    An example pathpoint database that persists it's data on disk.

    It persists it's store every :meth:`~smokclient.extras.BasePathpointDatabase.checkpoint` call.

    :param path: path to file containing pickled data.
    """

    def __init__(self, path: str):
        super().__init__()
        self.__path = path
        self.last_pathpoint_value = {}
        if os.path.exists(path):
            try:
                with open(path, 'rb') as f_in:
                    self.__pathpoints, self.last_pathpoint_value = pickle.load(f_in)
            except pickle.PickleError:
                pass

    def on_new_data(self, pathpoint: str, timestamp: Number,
                    value_or_exception: ValueOrExcept) -> None:
        self.last_pathpoint_value[pathpoint] = timestamp, value_or_exception
        super().on_new_data(pathpoint, timestamp, value_or_exception)

    def get_current_value(self, pathpoint: str) -> tp.Tuple[Number, PathpointValueType]:
        if pathpoint not in self.last_pathpoint_value:
            raise NotReadedError()
        val = self.last_pathpoint_value[pathpoint]
        if isinstance(val[1], OperationFailedError):
            raise val[1]
        return val

    @Monitor.synchronized
    def checkpoint(self) -> None:
        with open(self.__path, 'wb') as f_out:
            pickle.dump((self.__pathpoints, self.last_pathpoint_value), f_out)
