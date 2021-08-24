import queue
import logging
import typing as tp

from satella.coding import queue_get
from satella.coding.concurrent import TerminableThread
from satella.coding.decorators import retry
from satella.time import ExponentialBackoff
from satella.instrumentation.memory import get_size

from ..sync_workers.base import SyncError

MAX_LOG_BUFFER_SIZE = 20000
MAX_SIZE_LIMIT = 1024*1024
BUFFER_COEFFICIENT = 3  # data in MiniJSON might take more than data in memory
                        # multiply it by a constant, just to be safe
MAX_ITEM_LIMIT = 100    # in case that we are running on platforms that don't support get_size
logger = logging.getLogger(__name__)


class LogPublisherThread(TerminableThread):
    def __init__(self, device: 'SMOKDevice'):
        super().__init__(name='log publisher')
        self.device = device
        self.queue = queue.Queue()
        self.waiter = ExponentialBackoff()

    def get_all_messages(self, starting_msg: dict) -> tp.List[dict]:
        msgs = [starting_msg]
        try:
            size = get_size(starting_msg) * BUFFER_COEFFICIENT
            running_pypy = False
        except RuntimeError:
            size, running_pypy = 1, True    # running on PyPy
        while self.queue.qsize() and size < (MAX_ITEM_LIMIT if running_pypy else MAX_SIZE_LIMIT):
            msg = self.queue.get()
            msgs.append(msg)
            try:
                size += get_size(msg) * BUFFER_COEFFICIENT
            except RuntimeError:
                size += 1
        return msgs

    @queue_get('queue', timeout=5)
    def loop(self, msg) -> None:
        self.safe_sleep(1)  # wait for other records to become available
        while not self.device.allow_sync:
            # drop all messages on the floor if sync is disallowed
            while self.queue.qsize() > MAX_LOG_BUFFER_SIZE:
                self.queue.get()
        if self._terminating:
            return  # check if we have had a request for terminate in the meantime
        msgs = self.get_all_messages(msg)
        self.sync(msgs)

    @retry(3, exc_classes=SyncError)
    def sync(self, lst: tp.List[dict]) -> None:
        try:
            self.device.sync_worker.sync_logs(lst)
            self.device.on_successful_sync()
            self.waiter.success()
        except SyncError as e:
            self.waiter.failed()
            self.waiter.sleep()
            if e.is_no_link():
                self.device.on_failed_sync()
            if e.is_clients_fault():
                return      # it's better to lose packets than to re-submit them until failure
            raise

    def cleanup(self) -> None:
        if self.device.allow_sync:
            while self.queue.qsize() > 0:
                msgs = self.get_all_messages(self.queue.get())
                self.sync(msgs)
