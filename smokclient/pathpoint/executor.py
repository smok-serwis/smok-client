from concurrent.futures import wait

import requests
from satella.coding import queue_get
from satella.coding.concurrent import TerminableThread
import queue

from smokclient.pathpoint.orders import Section, MessageOrder, WriteOrder, ReadOrder, Disposition

__all__ = ['OrderExecutorThread']


def execute_a_message(device, msg: MessageOrder) -> None:
    requests.post(device.url + '/v1/device/orders/message/' + msg.uuid, cert=device.cert)


class OrderExecutorThread(TerminableThread):
    def __init__(self, device, order_queue: queue.Queue):
        super().__init__(name='order executor')
        self.queue = order_queue
        self.futures_to_complete = []
        self.device = device

    def execute_a_section(self, section: Section):
        for order in section.orders:
            if isinstance(order, (WriteOrder, ReadOrder)):
                pp = order.pathpoint
                if pp not in self.device.pathpoints:
                    self.device.pathpoints[pp] = self.device.unknown_pathpoint_provider(pp)
                pathpoint = self.device.pathpoints[pp]

                if isinstance(order, WriteOrder):
                    fut = pathpoint.on_write(order.value, order.advise)
                elif isinstance(order, ReadOrder):
                    fut = pathpoint.on_read(order.advise)

                self.futures_to_complete.append(fut)
            elif isinstance(order, MessageOrder):
                execute_a_message(self.device, order)

        time_to_wait = section.max_wait()
        if time_to_wait is not None:
            self.safe_sleep(time_to_wait)

        while self.futures_to_complete and not self.terminating:
            self.futures_to_complete = wait(self.futures_to_complete, 5)[1]

    @queue_get('queue', 5)
    def loop(self, msg):
        if self.queue.qsize():
            sec = self.queue.peek()
            if msg.disposition == Disposition.JOINABLE and sec.disposition == Disposition.JOINABLE:
                msg += self.queue.get()

        self.execute_a_section(sec)
