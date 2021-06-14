import copy
import logging
import queue
import typing as tp
from concurrent.futures import wait, Future

from satella.coding import queue_get
from satella.coding.concurrent import TerminableThread, call_in_separate_thread
from satella.coding.decorators import retry
from satella.instrumentation import Traceback
from satella.time import time_ms, measure

from smok.exceptions import ResponseError, NotReadedError, OperationFailedError
from smok.extras.pp_database.base import BasePathpointDatabase
from smok.pathpoint.orders import Section, WriteOrder, ReadOrder, MessageOrder, Disposition, \
    SysctlOrder, Order
from smok.pathpoint.pathpoint import Pathpoint

logger = logging.getLogger(__name__)


def on_read_completed_factory(pp: Pathpoint) -> tp.Callable[[Future], None]:
    def on_read_completed(fut: Future):
        ts = time_ms()
        if fut.exception() is None:
            res = fut.result()
            if res is None:
                return
        else:
            res = fut.exception()
            if not isinstance(res, OperationFailedError):
                try:
                    raise res
                except Exception as e:
                    f = Traceback().pretty_format()
                    logger.error('got %s while processing a read, stack trace is %s', e, f)
                    return
            if isinstance(res, NotReadedError):
                logger.error('A read future for %s returned NotReadedError, this is invalid, '
                             'ignoring',
                             pp.name)
                return
            res.timestamp = ts
        pp.set_new_value(ts, res)

    return on_read_completed


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


class OrderExecutorThread(TerminableThread):
    def __init__(self, device, order_queue: queue.Queue, data_to_sync: BasePathpointDatabase,
                 wait_before_startup: int = 0):
        super().__init__(name='order executor')
        self.queue = order_queue
        self.device = device
        self.data_to_sync = data_to_sync
        self.wait_before_startup = wait_before_startup

    def prepare(self) -> None:
        if self.wait_before_startup:
            self.safe_sleep(self.wait_before_startup)

    def process_orders(self, orders) -> tp.List[Order]:
        """
        Do some orders and return those that need to be retried
        """
        futures_to_complete = []
        orders_to_complete = []
        for order in orders:
            if isinstance(order, (WriteOrder, ReadOrder)):
                try:
                    pathpoint = self.device.get_pathpoint(order.pathpoint)
                except KeyError:
                    continue

                if isinstance(order, WriteOrder):
                    if not order.is_valid():
                        continue
                    fut = pathpoint.on_write(order.value, order.advise)
                    if fut is None:
                        continue
                    fut.add_done_callback(on_write_completed)
                elif isinstance(order, ReadOrder):
                    if pathpoint.can_read():
                        try:
                            fut = pathpoint.on_read(order.advise)  # type: Future
                            if not isinstance(fut, Future):
                                if fut is not None:
                                    pathpoint.set_new_value(time_ms(), fut)
                            else:
                                fut.add_done_callback(on_read_completed_factory(pathpoint))
                        except OperationFailedError as e:
                            pathpoint.set_new_value(time_ms(), e)
                        except Exception as e:
                            logger.error('Read operation for %s raised %s, ignoring',
                                         pathpoint.name, e, exc_info=e)
                    continue
            elif isinstance(order, MessageOrder):

                @call_in_separate_thread()
                @retry(6, ResponseError)
                def execute_a_message(uuid: str) -> Future:
                    self.device.api.post('/v1/device/orders/message/' + uuid)

                fut = execute_a_message(order.uuid)
            elif isinstance(order, SysctlOrder):
                self.device.execute_sysctl(order.op_type, order.op_args)
            else:
                continue
            orders_to_complete.append(order)
            futures_to_complete.append(fut)

        new_futures_to_complete = copy.copy(futures_to_complete)
        while new_futures_to_complete and not self.terminating:
            new_futures_to_complete = wait(new_futures_to_complete, 5)[1]

        if self.terminating:
            return []

        orders_to_retry = []
        for future, order in zip(futures_to_complete, orders_to_complete):
            if isinstance(future.exception(), (ResponseError, OperationFailedError)):
                if order.fail():
                    orders_to_retry.append(order)
        return orders_to_retry

    def execute_a_section(self, section: Section) -> None:
        from smok.client import SMOKDevice

        # Do we need to sync all sections?
        if section.disposition == Disposition.CANNOT_JOIN:
            self.device.sync_sections(lambda: self.terminating)

        if self.terminating:
            return

        orders = section.orders

        if section.mark_as_being_executed():
            if self.device.__class__.execute_section is SMOKDevice.execute_section:
                with measure() as measurement:
                    while orders and not self.terminating:
                        orders = self.process_orders(orders)

                time_to_wait = section.max_wait()
                if time_to_wait is not None:
                    if measurement() < time_to_wait:
                        self.safe_sleep(time_to_wait - measurement())

            else:
                self.device.execute_section(section)
        section.mark_as_done()

    @queue_get('queue', 5)
    def loop(self, section: Section):
        if self.queue.qsize():
            next_section = self.queue.peek()  # type: Section
            if section.is_joinable() and next_section.is_joinable():
                section += self.queue.get()

        self.execute_a_section(section)
