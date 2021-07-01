import logging
import typing as tp

from .base import BaseSyncWorker, SyncError
from ..exceptions import ResponseError

logger = logging.getLogger(__name__)


class HTTPSyncWorker(BaseSyncWorker):

    def sync_pathpoints(self, data: tp.List[dict]):
        try:
            self.api.post('/v1/device/pathpoints', json=data, timeout=40)
        except ResponseError as e:
            raise SyncError(e.is_no_link(), e.status_code // 100 == 4)

    def sync_logs(self, data: tp.List[dict]):
        try:
            self.api.put('/v1/device/device_logs', json=data, timeout=20)
        except ResponseError as e:
            raise SyncError(e.is_no_link(), e.status_code // 100 == 4)

    def __init__(self, device: 'SMOKDevice'):
        super().__init__(device, False)
        self.api = device.api

    def close(self):
        pass
