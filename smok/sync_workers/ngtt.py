import typing as tp

from satella.coding import reraise_as

from ngtt.exceptions import ConnectionFailed
from smok.sync_workers.base import BaseSyncWorker, SyncError
from ngtt.uplink import NGTTConnection


class NGTTSyncWorker(BaseSyncWorker):
    @reraise_as(ConnectionFailed, SyncError)
    def sync_logs(self, data: tp.List[dict]):
        self.connection.stream_logs(data)

    def __init__(self, device: 'SMOKDevice'):
        super().__init__(device)
        self.connection = NGTTConnection(device.temp_file_for_cert,
                                         device.temp_file_for_key)

    def close(self):
        self.connection.close()
