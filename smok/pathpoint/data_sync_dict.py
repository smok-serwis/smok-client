import typing as tp

from satella.coding import Monitor
from satella.coding.concurrent import Condition
from satella.coding.structures import DirtyDict
from satella.time import time_ms

from .typing import PathpointValueType
from ..exceptions import OperationFailedError, OperationFailedReason


class DataSyncDict(DirtyDict, Monitor):
    def __init__(self):
        super().__init__()
        Monitor.__init__(self)
        self.updated_condition = Condition()

    def on_readed_successfully(self, pathpoint: str, value: PathpointValueType,
                               timestamp: tp.Optional[float] = None) -> None:
        self.append(pathpoint, timestamp or time_ms(), value)

    @Monitor.synchronized
    def append(self, pathpoint, timestamp, value) -> None:
        tpl = (timestamp, value)
        if pathpoint not in self:
            self[pathpoint] = [tpl]
        else:
            ts_last = self[pathpoint][-1][0]
            if timestamp > ts_last:
                self[pathpoint].append(tpl)
        self.dirty = True
        self.updated_condition.notify()

    def add_from_json(self, dct: tp.List[dict]) -> None:
        for entry in dct:
            pp_name = entry['path']
            for value in entry['values']:
                if 'error_code' in value:
                    val = OperationFailedError(OperationFailedReason(value['error_code']))
                else:
                    val = value['value']
                self.append(pp_name, value['timestamp'], val)

    @Monitor.synchronized
    def to_json(self) -> tp.List[dict]:
        output = []
        for pathpoint, pathpoint_values in self.items():
            values = []
            for timestamp, value in pathpoint_values:
                if isinstance(value, OperationFailedError):
                    v = [False, int(timestamp), value.reason.value]
                else:
                    v = [int(timestamp), value]
                values.append(v)
            output.append({'path': pathpoint,
                           'values': values})
        self.clear()
        self.clear_dirty()
        return output

    def on_read_failed(self, pathpoint: str, error: OperationFailedError,
                       timestamp: tp.Optional[float] = None) -> None:
        self.append(pathpoint, timestamp or time_ms(), error)
