import typing as tp
import queue

from satella.coding import queue_get
from satella.coding.concurrent import TerminableThread
from satella.coding.decorators import retry

from ..exceptions import ResponseError


MAX_SYNC_AT_ONCE = 50
MAX_LOG_BUFFER_SIZE = 20000

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
    def loop(self, msg):
        while not self.device.allow_sync:
            while self.queue.qsize() > MAX_LOG_BUFFER_SIZE:
                self.queue.get()
            self.safe_sleep(10)
        if self._terminating:
            return
        msgs = self.get_all_messages(msg)
        self.sync(msgs)

    @retry(3, exc_classes=ResponseError)
    def sync(self, lst: tp.List[dict]):
        self.device.api.put('/v1/device/device_logs', json=lst, timeout=20)

    def cleanup(self):
        if self.device.allow_sync:
            while self.queue.qsize() > 0:
                msgs = self.get_all_messages(self.queue.get())
                self.sync(msgs)
