import os
import queue
import ssl
import typing as tp
import io
import tempfile


import pkg_resources
import requests

from smokclient.basics import SlaveDeviceInfo, DeviceInfo, Environment
from smokclient.certificate import get_device_info
from smokclient.pathpoint.reader import OrderExecutorThread


class SMOKDevice:
    """
    A base class for a SMOK device

    :param cert: either a path to or a file-like object containing the device certificate
    :param priv_key: either a path to or a file-like object containing the device private key
    """
    __slots__ = ('temp_file_for_cert', 'temp_file_for_key', 'device_id',
                 'environment', 'cert', 'url', 'executor', 'getter')

    def __init__(self, cert: tp.Union[str, io.StringIO],
                 priv_key: tp.Union[str, io.StringIO]):
        self.temp_file_for_cert = None
        if not isinstance(cert, str):
            with tempfile.NamedTemporaryFile('w', delete=False) as cert_file:
                cert_file.write(cert.read())
            cert = self.temp_file_for_cert = cert_file.name

        self.temp_file_for_key = None
        if not isinstance(priv_key, str):
            with tempfile.NamedTemporaryFile('w', delete=False) as key_file:
                key_file.write(priv_key.read())
            priv_key = self.temp_file_for_key = key_file.name

        self.cert = cert, priv_key

        with open(cert, 'rb') as fin:
            cert_data = fin.read()

        self.device_id, self.environment = get_device_info(cert_data)
        if self.environment == Environment.PRODUCTION:
            self.url = 'https://api.smok.co'
        elif self.environment == Environment.STAGING:
            self.url = 'http://api.test.smok-serwis.pl'
        elif self.environment == Environment.LOCAL_DEVELOPMENT:
            self.url = 'http://http-api'

        order_queue = queue.Queue()
        # self.executor = OrderExecutorThread(order_queue).start()
        # self.getter = OrderGetterThread(order_queue).start()

    def __del__(self) -> None:
        if self.temp_file_for_cert:
            os.unlink(self.temp_file_for_cert)
        if self.temp_file_for_key:
            os.unlink(self.temp_file_for_key)

    def get_device_info(self) -> DeviceInfo:
        resp = requests.get(self.url+'/v1/device', cert=self.cert)
        return DeviceInfo.from_json(resp.json())

