import copy
import logging
import queue
import time
import typing as tp
from concurrent.futures import wait, Future

from satella.coding import queue_get
from satella.coding.concurrent import TerminableThread, call_in_separate_thread
from satella.coding.decorators import retry
from satella.instrumentation import Traceback
from satella.time import time_ms, measure

from smok.exceptions import ResponseError, NotReadedError, OperationFailedError
from smok.extras.pp_database.base import BasePathpointDatabase
from smok.pathpoint.orders import Section, WriteOrder, ReadOrder, MessageOrder, Disposition
from smok.pathpoint.pathpoint import Pathpoint

logger = logging.getLogger(__name__)


def on_read_completed_factory(pp: Pathpoint) -> tp.Callable[[Future], None]:
    def on_read_completed(fut: Future):
        ts = time_ms()
        if fut.exception() is None:
            res = fut.result()
            if res is None:
                return
            pp.set_new_value(ts, res)
        else:
            exc = fut.exception()
            if not isinstance(exc, OperationFailedError):
                try:
                    raise exc
                except Exception as e:
                    f = Traceback().pretty_format()
                    logger.error('got %s while processing a read, stack trace is %s', e, f)
                    return
            if isinstance(exc, NotReadedError):
                logger.error('A read future for %s returned NotReadedError, this is invalid, '
                             'ignoring',
                             pp.name)
                return
            exc.timestamp = ts
            pp.set_new_value(ts, exc)

    return on_read_completed


def verify_write_factory(pp: Pathpoint) -> tp.Callable[[Future], None]:
    def on_write_completed(fut: Future):
        if fut.exception() is not None:
            exc = fut.exception()
            if not isinstance(exc, OperationFailedError):
                try:
                    raise exc
                except Exception as e:
                    f = Traceback().pretty_format()
                    logger.error('got %s while processing a write, stack trace is %s, '
                                 'assuming the write got through', e, f)
                    return

    return on_write_completed


class OrderExecutorThread(TerminableThread):
    def __init__(self, device, order_queue: queue.Queue, data_to_sync: BasePathpointDatabase):
        super().__init__(name='order executor')
        self.queue = order_queue
        self.device = device
        self.data_to_sync = data_to_sync

    def process_orders(self, orders):
        futures_to_complete = []
        orders_to_complete = []
        for order in orders:
            if isinstance(order, (WriteOrder, ReadOrder)):
                try:
                    pathpoint = self.device.get_pathpoint(order.pathpoint)
                except KeyError:
                    logger.info('Got order for unavailable pathpoint %s', order.pathpoint)
                    continue

                if isinstance(order, WriteOrder):
                    logger.warning(f'Executing %s to %s', order.pathpoint, order.value)
                    if not order.is_valid():
                        continue
                    fut = pathpoint.on_write(order.value, order.advise)
                    fut.add_done_callback(verify_write_factory(pathpoint))
                elif isinstance(order, ReadOrder):
                    fut = pathpoint.on_read(order.advise)  # type: Future
                    fut.add_done_callback(on_read_completed_factory(pathpoint))

            elif isinstance(order, MessageOrder):

                @call_in_separate_thread()
                @retry(6, ResponseError)
                def execute_a_message(uuid: str) -> Future:
                    self.device.api.post('/v1/device/orders/message/' + uuid)

                fut = execute_a_message(order.uuid)
            else:
                continue
            orders_to_complete.append(order)
            futures_to_complete.append(fut)

        new_futures_to_complete = copy.copy(futures_to_complete)
        while new_futures_to_complete and not self.terminating:
            new_futures_to_complete = list(wait(new_futures_to_complete, 5)[1])

        orders_to_retry = []
        for future, order in zip(futures_to_complete, orders_to_complete):
            if isinstance(future.exception(), OperationFailedError):
                if order.fail():
                    orders_to_retry.append(order)
        return orders_to_retry

    def execute_a_section(self, section: Section) -> None:
        from smok.client import SMOKDevice

        # Do we need to sync all sections?
        if section.disposition == Disposition.CANNOT_JOIN:
            self.device.sync_sections()

        orders = section.orders

        if self.device.__class__.execute_section is SMOKDevice.execute_section:
            if not section.future.set_running_or_notify_cancel():
                return  # Section cancelled

            with measure() as measurement:
                while orders:
                    orders = self.process_orders(orders)

            time_to_wait = section.max_wait()
            if time_to_wait is not None:
                if measurement() < time_to_wait:
                    self.safe_sleep(time_to_wait-measurement())

            section.future.set_result(None)
        else:
            logger.warning(f'Utilizing custom executor')
            self.device.execute_section(section)

    @queue_get('queue', 5)
    def loop(self, section: Section):
        if self.queue.qsize():
            next_section = self.queue.peek()  # type: Section
            if section.is_joinable() and next_section.is_joinable():
                section += self.queue.get()


        self.execute_a_section(section)

