from satella.coding import queue_get
from satella.coding.concurrent import TerminableThread, IntervalTerminableThread
import requests
import queue

from smokclient.pathpoint.orders import sections_from_list, Section

__all__ = ['OrderExecutorThread', 'OrderGetterThread']


class OrderGetterThread(IntervalTerminableThread):
    def __init__(self, device, order_queue: queue.Queue):
        super().__init__(30, name='order getter')
        self.device = device
        self.queue = order_queue

    def loop(self) -> None:
        resp = requests.post(self.device.url+'/v1/device/orders')
        data = resp.json()

        if data:
            for section in sections_from_list(data):
                self.queue.put(section)


class OrderExecutorThread(TerminableThread):
    def __init__(self, device, order_queue: queue.Queue):
        super().__init__(name='order executor')
        self.queue = order_queue

    @queue_get('queue', 5)
    def loop(self, section: Section) -> None:
        pass
