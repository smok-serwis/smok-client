import logging
from concurrent.futures import Future

import minijson
from satella.coding import wraps, for_argument, silence_excs, rethrow_as
from satella.coding.optionals import Optional
from satella.exceptions import Empty
from satella.time import ExponentialBackoff

from ..orders import Order

import typing as tp
import select
from satella.coding.concurrent import TerminableThread

from ..exceptions import DataStreamSyncFailed, ConnectionFailed
from ..protocol import NGTTHeaderType
from .connection import NGTTSocket

logger = logging.getLogger(__name__)


def must_be_connected_else_raise(fun):
    @wraps(fun)
    def outer(self, *args, **kwargs):
        if not self.connected:
            raise ConnectionFailed(True)
        return fun(self, *args, **kwargs)

    return outer


class NGTTConnection(TerminableThread):
    """
    An interface to NGTT, also a thread maintaining connection in the background.

    Note that instantiating this object is the same as calling start. You do not need to call
    start on this object after you initialize it.

    :param cert_file: path to file with certificate. This file should contain only the device
        certificate, attaching entire certificate chain is not required.
    :param key_file: path to private key
    :param on_new_order: a callable taking only a single argument and returning nothing, the
        callable to call when a new order appears. Note that you have to call
        either :meth:`~ngtt.orders.Order.acknowledge` or :meth:`~ngtt.orders.Order.nack` for each
        received order. Leave at default (None) if orders are not meant to be fetched.

    :ivar connected (bool) is connection opened
    """

    def __init__(self, cert_file: str, key_file: str,
                 on_new_order: tp.Optional[tp.Callable[[Order], None]] = None):
        super().__init__(name='ngtt uplink')
        self.on_new_order = on_new_order
        self.cert_file = cert_file
        self.stopped = False
        self.key_file = key_file
        self.current_connection = None
        self.start()

    def stop(self, wait_for_completion: bool = True):
        """
        Stop this thread and the connection

        :param wait_for_completion: whether to wait for thread to terminate
        """
        if self.stopped:
            return
        self.terminate()
        if wait_for_completion:
            self.join()
        self.stopped = True

    def close(self):
        """
        Alias for :meth:`~ngtt.uplink.NGTTConnection.stop`.
        """
        self.stop()
        if self.current_connection is not None:
            self.current_connection.close()
            self.current_connection = None
            self.op_id_to_op = {}

    @property
    @silence_excs(AttributeError, returns=False)
    def connected(self) -> bool:
        """Are we connected to target server?"""
        return self.current_connection.connected

    def connect(self):
        if self.connected:
            return
        eb = ExponentialBackoff(1, 30, self.safe_sleep)
        while not self.terminating and not self.connected:
            try:
                self.current_connection = NGTTSocket(self.cert_file, self.key_file)
                self.current_connection.connect()
                if self.on_new_order:
                    self.current_connection.send_frame(0, NGTTHeaderType.FETCH_ORDERS)
            except ConnectionFailed as e:
                logger.warning('Failure reconnecting', exc_info=e)
                eb.failed()
                eb.sleep()

            if self.terminating:
                return

    @must_be_connected_else_raise
    @for_argument(None, minijson.dumps)
    def sync_pathpoints(self, data) -> Future:
        """
        Try to synchronize pathpoints.

        This will survive multiple reconnection attempts.

        :param data: exactly the same thing that you would submit to POST
        at POST https://api.smok.co/v1/device/
        :return: a Future telling you whether this succeeds or fails. If succeeds, it will
            end with a result of None, if fails, it will end with a
            :class:`~ngtt.exceptions.DataStreamSyncFailed`
        """
        fut = Future()
        fut.set_running_or_notify_cancel()
        try:
            tid = self.current_connection.id_assigner.allocate_int()
        except Empty as e:
            logger.error('Ran out of IDs with a NGTT connection', exc_info=e)
            raise ConnectionFailed(False, 'Ran out of IDs to assign')

        self.current_connection.send_frame(tid, NGTTHeaderType.DATA_STREAM, data)
        self.current_connection.futures[tid] = fut
        return fut

    def inner_loop(self):
        self.current_connection.try_ping()
        ccon = [self.current_connection]
        rx, wx, ex = select.select(ccon,
                                   ccon if self.current_connection.wants_write else [], [],
                                   1)
        if wx:
            with rethrow_as(ConnectionResetError, ConnectionFailed):
                self.current_connection.try_send()
        if not rx:
            return
        frame = self.current_connection.recv_frame()
        if frame is None:
            return
        if frame.packet_type == NGTTHeaderType.PING:
            self.current_connection.got_ping()
        elif frame.packet_type == NGTTHeaderType.ORDER:
            try:
                data = frame.real_data
            except ValueError:
                logger.error('Received invalid JSON over the wire')
                raise ConnectionFailed(False, 'Got invalid JSON')
            order = Order(data, frame.tid, self.current_connection)
            self.on_new_order(order)
        elif frame.packet_type in (
                NGTTHeaderType.DATA_STREAM_REJECT, NGTTHeaderType.DATA_STREAM_CONFIRM):
            tid = frame.tid
            if tid in self.current_connection.futures:
                self.current_connection.id_assigner.mark_as_free(tid)
                # Assume it's a data stream running
                fut = self.current_connection.futures.pop(tid)

                if frame.packet_type == NGTTHeaderType.DATA_STREAM_CONFIRM:
                    fut.set_result(None)
                elif frame.packet_type == NGTTHeaderType.DATA_STREAM_REJECT:
                    fut.set_exception(DataStreamSyncFailed())
            else:
                logger.info('This was an unknown confirmation')

    def loop(self) -> None:
        try:
            self.connect()
        except ConnectionFailed as e:
            logger.warning('Failure during connect', exc_info=e)
            return

        if self.terminating:
            return

        try:
            self.inner_loop()
        except ConnectionFailed as e:
            logger.warning('Connection failed', exc_info=e)
            self.cleanup()

    def cleanup(self):
        Optional(self.current_connection).close()
        self.current_connection = None

    @must_be_connected_else_raise
    @for_argument(None, minijson.dumps)
    def stream_logs(self, data: tp.List) -> None:
        """
        Stream logs to the server

        This will work on a best-effort basis.

        :param data: the same thing that you would PUT /v1/device/device_logs
        """
        self.current_connection.send_frame(0, NGTTHeaderType.LOGS, data)
