import queue

from satella.coding import silence_excs
from satella.coding.concurrent import IntervalTerminableThread

from smokclient.exceptions import ResponseError
from smokclient.pathpoint.orders import sections_from_list


class OrderGetterThread(IntervalTerminableThread):
    def __init__(self, device, order_queue: queue.Queue):
        super().__init__(30, name='order getter')
        self.device = device
        self.queue = order_queue

    @silence_excs(ResponseError)
    def loop(self) -> None:
        resp = self.device.api.post('/v1/device/orders')

        if resp:
            for section in sections_from_list(resp):
                self.queue.put(section)
