import queue

from satella.coding.concurrent import IntervalTerminableThread
import requests

from .orders import sections_from_list


class OrderGetterThread(IntervalTerminableThread):
    def __init__(self, device, order_queue: queue.Queue):
        super().__init__(30, name='order getter')
        self.device = device
        self.queue = order_queue

    def loop(self) -> None:
        resp = requests.post(self.device.url+'/v1/device/orders')
        if resp.status_code != 200:
            return
        data = resp.json()

        if data:
            for section in sections_from_list(data):
                self.queue.put(section)
