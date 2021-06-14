import queue
import logging
import typing as tp

from satella.coding import queue_get
from satella.coding.concurrent import TerminableThread
from satella.coding.decorators import retry

from ..sync_workers.base import SyncError

MAX_SYNC_AT_ONCE = 50
MAX_LOG_BUFFER_SIZE = 20000
logger = logging.getLogger(__name__)


class LogPublisherThread(TerminableThread):
    def __init__(self, device: 'SMOKDevice'):
        super().__init__(name='log publisher')
        self.device = device
        self.queue = queue.Queue()

    def get_all_messages(self, starting_msg: dict) -> tp.List[dict]:
        msgs = [starting_msg]
        while self.queue.qsize() and len(msgs) < MAX_SYNC_AT_ONCE:
            msgs.append(self.queue.get())
        return msgs

    @queue_get('queue', timeout=5)
    def loop(self, msg) -> None:
        self.safe_sleep(1)  # wait for other records to become available
        while not self.device.allow_sync:
            while self.queue.qsize() > MAX_LOG_BUFFER_SIZE:
                self.queue.get()
            self.safe_sleep(10)
        if self._terminating:
            return
        msgs = self.get_all_messages(msg)
        self.sync(msgs)

    @retry(3, exc_classes=SyncError)
    def sync(self, lst: tp.List[dict]):
        try:
            try:
                self.device.sync_worker.sync_logs(lst)
                self.device.on_successful_sync()
            except Exception as e:
                logger.error('exception %s', e, exc_info=e)
                raise
        except SyncError as e:
            if e.is_no_link():
                self.device.on_failed_sync()
            raise

    def cleanup(self) -> None:
        if self.device.allow_sync:
            while self.queue.qsize() > 0:
                msgs = self.get_all_messages(self.queue.get())
                self.sync(msgs)
