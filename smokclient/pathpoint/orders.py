import time
import typing as tp
import enum

from smokclient.pathpoint.pathpoint import PathpointValueType


__all__ = ['AdviseLevel', 'Disposition', 'Order', 'ReadOrder', 'WriteOrder',
           'WaitOrder', 'MessageOrder', 'Section', 'sections_from_list']


class AdviseLevel(enum.IntEnum):
    ADVISE = 0
    FORCE = 1


class Order:
    """Base class for all orders"""
    __slots__ = ()


class MessageOrder(Order):
    __slots__ = ('uuid', )

    def __init__(self, uuid: str):
        self.uuid = uuid

    @classmethod
    def from_json(cls, dct: dict) -> 'MessageOrder':
        return MessageOrder(dct['uuid'])


class WaitOrder(Order):
    __slots__ = ('period', )

    def __init__(self, period: float):
        self.period = period

    @classmethod
    def from_json(cls, dct: dict) -> 'WaitOrder':
        return WaitOrder(dct['time'])


class WriteOrder(Order):
    __slots__ = ('pathpoint', 'value', 'advise', 'stale_after')

    def __init__(self, pathpoint: str, value: PathpointValueType, advise: AdviseLevel, stale_after: tp.Optional[float]):
        self.pathpoint = pathpoint
        self.value = value
        self.advise = advise
        self.stale_after = stale_after

    def is_valid(self) -> bool:
        if self.stale_after is None:
            return True
        return self.stale_after > time.time()

    @classmethod
    def from_json(cls, dct: dict) -> 'WriteOrder':
        return WriteOrder(dct['path'], dct['value'], AdviseLevel(dct.get('advise', 0)),
                          dct.get('stale_after'))


class ReadOrder(Order):
    def __init__(self, pathpoint: str, advise: AdviseLevel):
        self.pathpoint = pathpoint
        self.advise = advise

    @classmethod
    def from_json(cls, dct: dict) -> 'ReadOrder':
        return ReadOrder(dct['path'], AdviseLevel(dct.get('advise', 0)))


def orders_from_list(lst: tp.List[dict]) -> tp.List[Order]:
    orders = []
    for order in lst:
        order_type = order['type']
        if order_type == 'message':
            o = MessageOrder.from_json(order)
        elif order_type == 'read':
            o = ReadOrder.from_json(order)
        elif order_type == 'wait':
            o = WaitOrder.from_json(order)
        elif order_type == 'write':
            o = WriteOrder.from_json(order)
        else:
            o = None

        if o:
            orders.append(o)
    return orders


class Disposition(enum.IntEnum):
    JOINABLE = 0
    CANNOT_JOIN = 1


class Section:
    def __init__(self, orders: tp.List[Order], disposition: Disposition = Disposition.JOINABLE):
        self.orders = orders
        self.disposition = disposition

    @classmethod
    def from_json(cls, dct: dict):
        return Section([orders_from_list(dct['orders']), Disposition(dct.get('disposition', 0))])

    def __iadd__(self, other: 'Section') -> 'Section':
        self.orders.extend(other.orders)
        return self

    def __add__(self, other: 'Section') -> 'Section':
        return Section(self.orders + other.orders)

    def is_joinable(self) -> bool:
        return self.disposition == Disposition.JOINABLE

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
