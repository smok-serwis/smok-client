import typing as tp

from satella.coding import reraise_as

from .base import BaseSyncWorker, SyncError
from ..exceptions import ResponseError


class HTTPSyncWorker(BaseSyncWorker):
    @reraise_as(ResponseError, SyncError)
    def sync_logs(self, data: tp.List[dict]):
        try:
            self.api.put('/v1/device/device_logs', json=data, timeout=20)
        except ResponseError as e:
            raise SyncError(e.is_no_link())

    def __init__(self, device: 'SMOKDevice'):
        super().__init__(device)
        self.api = device.api

    def close(self):
        pass
