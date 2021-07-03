import logging
import os
import socket
import ssl
import tempfile
import time
import typing as tp
from ssl import SSLContext, PROTOCOL_TLS_CLIENT, SSLError, CERT_REQUIRED

from satella.coding import silence_excs, reraise_as, Closeable, RMonitor
from satella.coding.concurrent import IDAllocator
from satella.coding.optionals import Optional
from satella.exceptions import Empty
from satella.files import read_in_file

from smok.client import get_dev_ca_cert, get_root_cert
from smok.client.certificate import get_device_info
from ..exceptions import ConnectionFailed
from ..protocol import NGTTHeaderType, STRUCT_LHH, env_to_hostname, NGTTFrame

PING_INTERVAL_TIME = 30
INTERVAL_TIME_NO_RESPONSE_KILL = 90
INTERVAL_TIME_NO_RESPONSE_READ_KILL = 120
logger = logging.getLogger(__name__)


class NGTTSocket(Closeable):
    """
    The agreement is that after last write you have 60 seconds to write something.

    We keep last_read as our-side keepalive
    """
    @property
    def wants_write(self) -> bool:
        return bool(self.w_buffer)

    def __init__(self, cert_file: str, key_file: str):
        self.monitor = RMonitor()
        self.socket = None
        self.connected = False
        environment = get_device_info(read_in_file(cert_file))[1]
        self.host = env_to_hostname(environment)
        self.cert_file = cert_file
        self.key_file = key_file
        self.buffer = bytearray()
        self.w_buffer = bytearray()
        self.ping_id = None
        self.futures = {}
        self.last_read = time.monotonic()
        self.last_write = time.monotonic()
        with tempfile.NamedTemporaryFile('wb', delete=False) as chain_file:
            chain_file.write(get_dev_ca_cert())
            chain_file.write(b'\n')
            chain_file.write(get_root_cert())
            chain_file.close()
            self.chain_file_name = chain_file.name

        self.id_assigner = IDAllocator(start_at=1, top_limit=0x8000)
        super().__init__()

    @RMonitor.synchronize_on_attribute('monitor')
    def send_frame(self, tid: int, header: NGTTHeaderType, data: bytes = b'') -> None:
        """
        Schedule a frame to be sent.

        This will be actually send in a background thread. May have a delay of
        up to 1 second, which is acceptable.

        :param tid: transaction ID
        :param header: packet type
        :param data: data to send
        """
        if self.closed:
            return
        self.w_buffer.extend(STRUCT_LHH.pack(len(data), tid, header.value))
        self.w_buffer.extend(data)

    @RMonitor.synchronize_on_attribute('monitor')
    @reraise_as((BrokenPipeError, ssl.SSLError), ConnectionFailed)
    @silence_excs(ssl.SSLWantWriteError)
    def try_send(self):
        """
        Try to send some data. This is called only when the socket is writeable.
        """
        if self.w_buffer:
            data_sent = self.socket.send(self.w_buffer)
            self.last_write = time.monotonic()
            del self.w_buffer[:data_sent]

    @RMonitor.synchronize_on_attribute('monitor')
    def try_ping(self):
        delta = time.monotonic() - self.last_write

        if time.monotonic() - self.last_read > INTERVAL_TIME_NO_RESPONSE_READ_KILL \
                and self.ping_id is not None:
            raise ConnectionFailed(False, 'timed out due to ping (read-side)')
        elif delta > INTERVAL_TIME_NO_RESPONSE_KILL \
                and self.ping_id is not None:
            raise ConnectionFailed(False, 'timed out due to ping (write-side)')
        elif delta > PING_INTERVAL_TIME and self.ping_id is None:
            try:
                self.ping_id = self.id_assigner.allocate_int()
            except Empty as e:
                logger.error('Ran out of IDs while processing ping send')
                raise ConnectionFailed(False, 'ran out of IDs on ping') from e
            self.send_frame(self.ping_id, NGTTHeaderType.PING)

    @RMonitor.synchronize_on_attribute('monitor')
    def got_ping(self):
        if self.ping_id is not None:
            self.id_assigner.mark_as_free(self.ping_id)
            self.last_read = time.monotonic()
            self.ping_id = None

    def fileno(self) -> int:
        return self.socket.fileno()

    @RMonitor.synchronize_on_attribute('monitor')
    @reraise_as((BrokenPipeError, ssl.SSLError, ConnectionResetError), ConnectionFailed)
    @silence_excs(ssl.SSLWantReadError)
    def recv_frame(self) -> tp.Optional[NGTTFrame]:
        """
        Receive a frame from remote socket, or None if nothing could be assembled as of now.

        This should only be called when it is determined that the socket is readable, for example
        via :code:`select`.

        :raises ConnectionFailed: connection closed
        :return: a tuple of transaction ID, header type, data
        """
        data = self.socket.recv(512)
        if not data:
            raise ConnectionFailed(False, 'gracefully closed')
        self.last_read = time.monotonic()
        self.buffer.extend(data)

        result = NGTTFrame.from_buffer(self.buffer)
        if result is None:
            return None

        length, frame = result
        del self.buffer[:length]
        return frame

    @RMonitor.synchronize_on_attribute('monitor')
    def close(self):
        if super().close():
            self.disconnect()
            try:
                os.unlink(self.chain_file_name)
            except OSError as e:
                logger.error('Failure to remove certificate chain file %s', self.chain_file_name,
                             exc_info=e)

            for future in self.futures.values():
                future.set_exception(ConnectionFailed(False, 'closing the link'))

    @RMonitor.synchronize_on_attribute('monitor')
    def disconnect(self):
        """
        Disconnect from the remote host
        """
        with silence_excs(OSError):
            Optional(self.socket).close()
        self.socket = None
        self.connected = False

    @RMonitor.synchronize_on_attribute('monitor')
    def connect(self):
        """
        Connect to remote host

        :raises SSLError: an error occurred
        :raises RuntimeError: upon connection being closed
        """
        if self.closed:
            raise RuntimeError('This connection is closed!')
        if self.connected:
            return
        ssl_context = SSLContext(PROTOCOL_TLS_CLIENT)
        ssl_context.load_verify_locations(self.chain_file_name)
        ssl_context.load_cert_chain(self.cert_file, self.key_file)
        ssl_context.verify_mode = CERT_REQUIRED
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        ssl_sock = ssl_context.wrap_socket(sock, server_hostname=self.host)
        try:
            ssl_sock.connect((self.host, 2408))
            ssl_sock.do_handshake()
        except ConnectionRefusedError as e:
            ssl_sock.close()
            raise ConnectionFailed(True) from e
        except (socket.error, SSLError) as e:
            ssl_sock.close()
            raise ConnectionFailed(True) from e
        self.socket = ssl_sock
        self.socket.setblocking(False)
        self.last_read = time.monotonic()
        self.last_write = time.monotonic()
        self.buffer = bytearray()
        self.w_buffer = bytearray()
        self.connected = True
        self.ping_id = None
        logger.debug('Successfully reconnected')
