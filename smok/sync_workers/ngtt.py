import logging
import time
import typing as tp

from ngtt.exceptions import ConnectionFailed, DataStreamSyncFailed
from ngtt.orders import Order
from smok.pathpoint.orders import sections_from_list
from smok.sync_workers.base import SyncError
from ngtt.uplink import NGTTConnection
from smok.sync_workers.http import HTTPSyncWorker

logger = logging.getLogger(__name__)


class NGTTSyncWorker(HTTPSyncWorker):
    """
    Note that this is ready to start when .executor on the device is ready
    """

    def __init__(self, device: 'SMOKDevice'):
        super().__init__(device)
        self.connection = NGTTConnection(device.temp_file_for_cert,
                                         device.temp_file_for_key,
                                         None if self.device.dont_do_orders else self.process_orders)
        self.has_async_orders = True
        time.sleep(5)  # Give it some time to connect

    def process_orders(self, orders: Order):
        sections = sections_from_list(orders.data)

        def confirm(fut):
            orders.acknowledge()

        sections[-1].future.add_done_callback(confirm)
        self.device.executor.queue.put_many(sections)

    def sync_pathpoints(self, data: tp.List[dict]):
        """
        :raises SyncError: on failure
        """
        try:
            fut = self.connection.sync_pathpoints(data)
            fut.result()
        except DataStreamSyncFailed as e:
            raise SyncError(False, True) from e
        except ConnectionFailed as e:
            raise SyncError(e.is_due_to_no_internet) from e

    def close(self):
        self.connection.close()
