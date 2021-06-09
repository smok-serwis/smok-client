import typing as tp

from satella.coding import reraise_as

from .base import BaseSyncWorker, SyncError
from ..exceptions import ResponseError


class HTTPSyncWorker(BaseSyncWorker):

    def sync_pathpoints(self, data: tp.List[dict]):
        try:
            self.api.post('/v1/device/pathpoints', json=data)
        except ResponseError as e:
            raise SyncError(e.is_no_link())

    @reraise_as(ResponseError, SyncError)
    def sync_logs(self, data: tp.List[dict]):
        try:
            self.api.put('/v1/device/device_logs', json=data, timeout=20)
        except ResponseError as e:
            raise SyncError(e.is_no_link())

    def __init__(self, device: 'SMOKDevice'):
        super().__init__(device, False)
        self.api = device.api



    def close(self):
        pass
