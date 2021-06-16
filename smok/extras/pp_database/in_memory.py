import copy
import typing as tp

from satella.coding import Monitor
from satella.coding.typing import Number

from .base import BaseDataToSynchronize, BasePathpointDatabase, ValueOrExcept
from ...exceptions import OperationFailedError, NotReadedError, OperationFailedReason
from ...pathpoint import PathpointValueType


class InMemoryDataToSynchronize(BaseDataToSynchronize):
    def negative_acknowledge(self) -> None:
        pass

    __slots__ = 'in_memory', 'data'

    def __init__(self, in_memory: 'InMemoryPathpointDatabase', data: tp.List):
        self.in_memory = in_memory
        self.data = data

    def to_json(self) -> tp.List:
        return self.data

    def acknowledge(self) -> None:
        timestamps_for_pathpoints = {}  # type: tp.Dict[str, Number]
        for pp in self.data:
            max_ts = max(v['timestamp'] for v in pp['values'])
            timestamps_for_pathpoints[pp['path']] = max_ts

        for pathpoint, timestamp in timestamps_for_pathpoints.items():
            self.in_memory.confirm_synced_up_to(pathpoint, timestamp)


class InMemoryPathpointDatabase(BasePathpointDatabase, Monitor):
    def get_archive_data(self, pathpoint: str, start: tp.Optional[Number],
                         stop: tp.Optional[Number]) -> tp.Iterator[tp.Tuple[Number, ValueOrExcept]]:
        return []

    @Monitor.synchronized
    def get_current_value(self, pathpoint: str) -> tp.Tuple[Number, PathpointValueType]:
        """
        Get the current value for given pathpoint

        :param pathpoint: name of the pathpoint
        :return: a tuple of (timestamp, value or exception)
        :raises NotReadedError: pathpoint has no last value
        """
        if pathpoint not in self.pathpoints:
            raise NotReadedError()

        lv = self.pathpoints[pathpoint][-1]
        if 'error_code' in lv:
            raise OperationFailedError(OperationFailedReason(lv['error_code']), lv['timestamp'])
        else:
            return lv['timestamp'], lv['value']

    @Monitor.synchronized
    def get_data_to_sync(self) -> tp.Optional[BaseDataToSynchronize]:
        if not self.pathpoints:
            return None
        data_to_sync = []
        for pathpoint, values in self.pathpoints.items():
            data_to_sync.append({'path': pathpoint, 'values': copy.copy(values)})
        return InMemoryDataToSynchronize(self, data_to_sync)

    @Monitor.synchronized
    def on_new_data(self, pathpoint: str, timestamp: Number, value_or_exception: ValueOrExcept):
        if isinstance(value_or_exception, OperationFailedError):
            datapoint = {'timestamp': timestamp, 'error_code': value_or_exception.reason.value}
        else:
            datapoint = {'timestamp': timestamp, 'value': value_or_exception}

        if pathpoint not in self.pathpoints:
            self.pathpoints[pathpoint] = [datapoint]
        else:
            if int(self.pathpoints[pathpoint][0]['timestamp']) < int(timestamp):
                self.pathpoints[pathpoint].append(datapoint)

    @Monitor.synchronized
    def confirm_synced_up_to(self, pathpoint: str, timestamp: Number) -> None:
        if pathpoint not in self.pathpoints:
            return
        for i, data in enumerate(self.pathpoints[pathpoint]):
            if data['timestamp'] > timestamp:
                break
        else:
            i = None

        if i is None:
            del self.pathpoints[pathpoint]
        else:
            self.pathpoints[pathpoint] = self.pathpoints[pathpoint][i:]

    def __init__(self):
        self.pathpoints = {}
        Monitor.__init__(self)

    def checkpoint(self) -> None:
        pass
