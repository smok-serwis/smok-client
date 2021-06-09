import typing as tp

from ngtt.exceptions import ConnectionFailed, DataStreamSyncFailed
from ngtt.orders import Order
from smok.pathpoint.orders import sections_from_list
from smok.sync_workers.base import BaseSyncWorker, SyncError
from ngtt.uplink import NGTTConnection


class NGTTSyncWorker(BaseSyncWorker):

    def sync_logs(self, data: tp.List[dict]):
        try:
            self.connection.stream_logs(data)
        except ConnectionFailed as e:
            raise SyncError(e.is_due_to_no_internet)

    def __init__(self, device: 'SMOKDevice'):
        super().__init__(device, True)
        self.connection = NGTTConnection(device.temp_file_for_cert,
                                         device.temp_file_for_key,
                                         self.process_orders)

    def process_orders(self, orders: Order):
        sections = sections_from_list(orders.data)
        sections[-1].future.add_done_callback(lambda fut: orders.acknowledge())
        for sec in sections:
            self.device.executor.queue.put(sec)

    def sync_pathpoints(self, data: tp.List[dict]):
        """
        :raises SyncError: on failure
        """
        try:
            self.connection.sync_pathpoints(data).result()
        except DataStreamSyncFailed:
            raise SyncError(False)

    def close(self):
        self.connection.close()
