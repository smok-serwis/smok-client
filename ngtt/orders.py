import typing as tp

from ngtt.protocol import NGTTHeaderType


class Order:
    """
    An order received from the server.

    Can be confirmed via :meth:`~ngtt.orders.Order.acknowledge` to signal to the server
    that it's been processed.
    """
    __slots__ = ('data', 'tid', 'sock', 'confirmed')

    def __init__(self, data: tp.Dict, tid: int, sock: 'NGTTSocket'):
        self.data = data
        self.tid = tid
        self.sock = sock
        self.confirmed = False

    def acknowledge(self):
        """
        Signal to the server that the order has been processed
        """
        if not self.confirmed:
            logger.debug('Confirming order no %s', self.tid)
            self.sock.send_frame(self.tid, NGTTHeaderType.ORDER_CONFIRM)
            self.confirmed = True

    def nack(self):
        """
        Signal the server that the order has been rejected
        """
        if not self.confirmed:
            self.sock.send_frame(self.tid, NGTTHeaderType.ORDER_REJECT)
            self.confirmed = True
