import logging
import queue
import time
import typing as tp
from concurrent.futures import wait, Future

from satella.coding import queue_get
from satella.coding.concurrent import TerminableThread, call_in_separate_thread
from satella.coding.decorators import retry

from smokclient.exceptions import ResponseError, NotReadedError
from smokclient.extras.pp_database.base import BasePathpointDatabase
from smokclient.pathpoint.orders import Section, WriteOrder, ReadOrder, MessageOrder, Disposition
from smokclient.pathpoint.pathpoint import Pathpoint

logger = logging.getLogger(__name__)


def on_read_completed_factory(oet: 'OrderExecutorThread',
                              pp: Pathpoint) -> tp.Callable[[Future], None]:
    def on_read_completed(fut: Future):
        ts = time.time()
        if fut.exception() is None:
            oet.data_to_sync.on_new_data(pp.name, ts, fut.result())
            pp.current_timestamp = time.time()
            pp.current_value = fut.result()
        else:
            exc = fut.exception()
            if isinstance(exc, NotReadedError):
                logger.error('A read future for %s returned NotReadedError, this is invalid')
                return
            exc.timestamp = ts
            oet.data_to_sync.on_new_data(pp.name, ts, exc)
            pp.current_timestamp = ts
            pp.current_value = fut.exception()

    return on_read_completed


class OrderExecutorThread(TerminableThread):
    def __init__(self, device, order_queue: queue.Queue, data_to_sync: BasePathpointDatabase):
        super().__init__(name='order executor')
        self.queue = order_queue
        self.futures_to_complete = []
        self.device = device
        self.data_to_sync = data_to_sync

    def execute_a_section(self, section: Section) -> None:
        from smokclient.client import SMOKDevice

        if self.device.execute_section is SMOKDevice.execute_section:
            # Do we need to sync all sections?
            if section.disposition == Disposition.CANNOT_JOIN:
                self.device.sync_sections()

            if not section.future.set_running_or_notify_cancel():
                return  # Section cancelled

            for order in section.orders:
                if isinstance(order, (WriteOrder, ReadOrder)):
                    try:
                        pathpoint = self.device.get_pathpoint(order.pathpoint)
                    except KeyError:
                        logger.warning('Got order for unavailable pathpoint %s' % (order.pathpoint,))
                        continue

                    if isinstance(order, WriteOrder):
                        if not order.is_valid():
                            continue
                        fut = pathpoint.on_write(order.value, order.advise)
                    elif isinstance(order, ReadOrder):
                        fut = pathpoint.on_read(order.advise)  # type: Future
                        fut.add_done_callback(on_read_completed_factory(self, pathpoint))

                elif isinstance(order, MessageOrder):

                    @call_in_separate_thread()
                    @retry(6, ResponseError)
                    def execute_a_message(uuid: str) -> Future:
                        self.device.api.post('/v1/device/orders/message/' + uuid)

                    fut = execute_a_message(order.uuid)
                else:
                    logger.warning('Unknown order type %s' % (order,))
                    continue
                self.futures_to_complete.append(fut)

            time_to_wait = section.max_wait()
            if time_to_wait is not None:
                self.safe_sleep(time_to_wait)

            while self.futures_to_complete and not self.terminating:
                self.futures_to_complete = list(wait(self.futures_to_complete, 5)[1])
            section.future.set_result(None)
        else:
            self.device.execute_section(section)

    @queue_get('queue', 5)
    def loop(self, section: Section):
        print(section)
        if self.queue.qsize():
            next_section = self.queue.peek()  # type: Section
            if section.is_joinable() and next_section.is_joinable():
                section += self.queue.get()

        self.execute_a_section(section)
