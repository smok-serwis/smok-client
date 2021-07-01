import enum
import logging
import time
import typing as tp
from concurrent.futures import Future

from satella.coding.structures import ReprableMixin
from satella.coding.concurrent import FutureCollection

from .typing import PathpointValueType

__all__ = ['AdviseLevel', 'Disposition', 'Order', 'ReadOrder', 'WriteOrder',
           'WaitOrder', 'MessageOrder', 'Section', 'sections_from_list',
           'SysctlOrder']

logger = logging.getLogger(__name__)


class AdviseLevel(enum.IntEnum):
    """
    Advise level specifies how hard should the device try to execute this command.
    """
    ADVISE = 0  #: Best-effort
    FORCE = 1  #: Nearly guarantees correct delivery, up to blocking the pipeline if need be


class Order:
    """Base class for all orders"""
    __slots__ = ()


class SysctlOrder(Order, ReprableMixin):
    """
    A sysctl order. These are completely user-defined.
    """
    _REPR_FIELDS = 'op_type', 'op_args'
    __slots__ = 'op_type', 'op_args'

    def __init__(self, op_type: str, op_args: str):
        self.op_type = op_type
        self.op_args = op_args

    def __str__(self) -> str:
        return repr(self)

    @classmethod
    def from_json(cls, dct: dict) -> 'SysctlOrder':
        return SysctlOrder(dct['op_type'], dct['op_args'])


class MessageOrder(Order, ReprableMixin):
    """
    A message order. Best executed with
    :meth:`smok.client.SMOKDevice._execute_message_order`
    """
    _REPR_FIELDS = 'uuid', 'times_retry'
    __slots__ = 'uuid', 'times_retry'

    def __init__(self, uuid: str):
        self.uuid = uuid
        self.times_retry = 3

    def __str__(self) -> str:
        return repr(self)

    def fail(self) -> bool:
        self.times_retry -= 1
        return bool(self.times_retry)

    @classmethod
    def from_json(cls, dct: dict) -> 'MessageOrder':
        return MessageOrder(dct['uuid'])


class WaitOrder(Order, ReprableMixin):
    """
    Order to wait a given amount of seconds

    :param period: seconds to wait
    """
    _REPR_FIELDS = ('period',)
    __slots__ = ('period',)

    def __init__(self, period: float):
        self.period = period

    @classmethod
    def from_json(cls, dct: dict) -> 'WaitOrder':
        return WaitOrder(dct['time'])

    def __str__(self) -> str:
        return repr(self)


class WriteOrder(Order, ReprableMixin):
    """
    Order to write a target value to target pathpoint

    :param pathpoint: name of pathpoint to write to
    :param value: value to write
    :param advise: advise level
    :param stale_after: optional timestamp in seconds, after which this write
        will be discarded
    """
    _REPR_FIELDS = 'pathpoint', 'value', 'advise', 'stale_after'
    __slots__ = 'pathpoint', 'value', 'advise', 'stale_after', 'repeat_count'

    def __init__(self, pathpoint: str, value: PathpointValueType, advise: AdviseLevel,
                 stale_after: tp.Optional[float] = None):
        self.pathpoint = pathpoint
        self.value = value
        self.advise = advise
        self.repeat_count = 10 if advise == AdviseLevel.FORCE else 1
        self.stale_after = stale_after

    def is_valid(self) -> bool:
        if self.stale_after is None:
            return True
        return self.stale_after > time.time()

    def __str__(self) -> str:
        return repr(self)

    def fail(self) -> bool:
        """
        Fail this order.

        Return whether to requeue it
        """
        self.repeat_count -= 1
        return bool(self.repeat_count)

    @classmethod
    def from_json(cls, dct: dict) -> 'WriteOrder':
        return WriteOrder(dct['path'], dct['value'], AdviseLevel(dct.get('advise', 0)),
                          dct.get('stale_after'))


class ReadOrder(Order, ReprableMixin):
    """
    An order to read a pathpoint

    :param pathpoint: pathpoint to read
    :param advise: advise level
    """
    _REPR_FIELDS = 'pathpoint', 'advise'

    def __init__(self, pathpoint: str, advise: AdviseLevel):
        self.pathpoint = pathpoint
        self.advise = advise
        self.repeat_count = 3 if AdviseLevel.ADVISE else 20

    def __str__(self) -> str:
        return repr(self)

    @classmethod
    def from_json(cls, dct: dict) -> 'ReadOrder':
        return ReadOrder(dct['path'], AdviseLevel(dct.get('advise', 0)))

    def fail(self) -> bool:
        """
        Fail this order.

        Return whether to requeue it
        """
        self.repeat_count -= 1
        return bool(self.repeat_count)


def orders_from_list(lst: tp.List[dict]) -> tp.List[Order]:
    orders = []
    for order in lst:
        try:
            order_type = order['type']
        except KeyError:
            logger.error('Received order (%s) without a type, ignoring', order)
            continue

        if order_type == 'message':
            o = MessageOrder.from_json(order)
        elif order_type == 'read':
            o = ReadOrder.from_json(order)
        elif order_type == 'sysctl':
            o = SysctlOrder.from_json(order)
        elif order_type == 'wait':
            o = WaitOrder.from_json(order)
        elif order_type == 'write':
            o = WriteOrder.from_json(order)
        else:
            logger.error('Received unknown order type of %s, ignoring', order_type)
            continue

        orders.append(o)
    return orders


class Disposition(enum.IntEnum):
    """
    A joinable quality of the section
    """
    JOINABLE = 0  #: this section can be joined to neighbouring JOINABLE sections
    CANNOT_JOIN = 1  #: this section cannot be joined to any sections


class Section(ReprableMixin):
    """
    A collection of orders.

    :param orders: a list of orders
    :param disposition: if Disposition.JOINABLE then this section can be joined with
        other sections. If Disposition.CANNOT_JOIN then all orders from this section
        will be executed before proceeding to next one

    :ivar future: a future that completes upon this section being finished.
        If this future is cancelled, and section did not start executing, it will be.
    """
    _REPR_FIELDS = 'orders', 'disposition'
    __slots__ = 'orders', 'disposition', 'future', 'cancelled'

    def __init__(self, orders: tp.List[Order] = None,
                 disposition: Disposition = Disposition.JOINABLE):

        self.future = FutureCollection([Future()])
        self.orders = orders or []
        self.disposition = disposition
        self.cancelled = False

    def __str__(self) -> str:
        return repr(self)

    def mark_as_done(self) -> None:
        """
        Should be invoked by your custom executor when executing this section completes.
        """
        self.future.set_result(None)

    def cancel(self) -> None:
        """
        Cancel the order
        """
        # we still need to execute the callbacks, as they might be holding an AMQP message
        # somewhere...
        self.cancelled = True

    def result(self, timeout: tp.Optional[float] = None):
        self.future.result(timeout)

    def __bool__(self) -> bool:
        return bool(self.orders)

    @classmethod
    def from_json(cls, dct: dict):
        return Section(orders_from_list(dct['orders']), Disposition(dct.get('disposition', 0)))

    def __iadd__(self, other: tp.Union[Order, 'Section', tp.Sequence['Section']]) -> 'Section':
        if isinstance(other, Order):
            self.orders.append(other)
        elif isinstance(other, tp.Sequence):
            self.orders.extend(other)
        else:
            self.orders.extend(other.orders)
            self.future += other.future
        return self

    def is_joinable(self) -> bool:
        return self.disposition == Disposition.JOINABLE

    def mark_as_being_executed(self) -> bool:
        """
        Mark this section as executed right now

        :return: whether is should be executed (False if cancelled)
        """
        self.future.set_running_or_notify_cancel()
        return not self.cancelled

    def max_wait(self) -> tp.Optional[float]:
        wait = None
        for order in (or_ for or_ in self.orders if isinstance(or_, WaitOrder)):
            if wait is None:
                wait = order.period
            else:
                if wait < order.period:
                    wait = order.period
        return wait


def sections_from_list(lst: tp.List[dict]) -> tp.List[Section]:
    return [Section.from_json(section) for section in lst]
