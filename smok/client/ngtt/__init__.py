import os
import socket

import tempfile
from ssl import SSLContext, PROTOCOL_TLS_CLIENT, SSLError

from smok.basics import Environment
from smok.client import get_root_cert


def get_host_name(device: 'SMOKDevice'):
    if device.environment == Environment.PRODUCTION:
        return 'api.smok.co'
    elif device.environment == Environment.STAGING:
        return 'api.test.smok-serwis.pl'
    else:
        return 'http-api'


class ConnectionFailed(Exception):
    pass


class NGTTSocket:
    def __init__(self, device: 'SMOKDevice', host: str):
        self.host = host
        self.device = device
        self.socket = None

        with tempfile.NamedTemporaryFile('w', delete=False) as chain_file:
            chain_file.write(self.device.cert_chain)
            self.chain_file_name = chain_file.name

    def __del__(self):
        os.unlink(self.chain_file_name)

    def disconnect(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def connect(self):
        if self.socket is not None:
            return
        ssl_context = SSLContext(PROTOCOL_TLS_CLIENT)
        ssl_context.load_verify_locations(cadata=get_root_cert().encode('utf-8'))
        ssl_context.load_cert_chain(self.chain_file_name,
                                    self.device.temp_file_for_key)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = get_host_name(self.device)
        ssl_sock = ssl_context.wrap_socket(sock, server_hostname=host)
        try:
            ssl_sock.connect((host, 2408))
            ssl_sock.do_handshake()
            self.socket = ssl_sock
        except (socket.error, SSLError):
            raise ConnectionFailed()

