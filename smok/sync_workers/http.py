import typing as tp

from satella.coding import reraise_as

from .base import BaseSyncWorker, SyncError
from ..exceptions import ResponseError


class HTTPSyncWorker(BaseSyncWorker):

    def sync_pathpoints(self, data: tp.List[dict]):
        try:
            self.api.post('/v1/device/pathpoints', minijson=data,
                          headers={'Content-Type': 'application/minijson'},
                          timeout=40)
        except ResponseError as e:
            raise SyncError(e.is_no_link(), e.status_code // 100 == 4)

    @reraise_as(ResponseError, SyncError)
    def sync_logs(self, data: tp.List[dict]):
        try:
            self.api.put('/v1/device/device_logs', minijson=data,
                         headers={'Content-Type': 'application/minijson'},
                         timeout=20)
        except ResponseError as e:
            raise SyncError(e.is_no_link(), e.status_code // 100 == 4)

    def __init__(self, device: 'SMOKDevice'):
        super().__init__(device, False)
        self.api = device.api



    def close(self):
        pass
