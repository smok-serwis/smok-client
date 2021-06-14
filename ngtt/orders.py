import logging
import typing as tp

from ngtt.protocol import NGTTHeaderType


logger = logging.getLogger(__name__)


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
            self.confirm_with(NGTTHeaderType.ORDER_CONFIRM)

    def confirm_with(self, c_type: NGTTHeaderType):
        self.sock.send_frame(self.tid, c_type)
        self.confirmed = True

    def nack(self):
        """
        Signal the server that the order has been rejected
        """
        if not self.confirmed:
            logger.debug('Confirming order no %s', self.tid)
            self.confirm_with(NGTTHeaderType.ORDER_REJECT)
