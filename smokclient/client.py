import os
import typing as tp
import io
import tempfile


import requests

from satella.coding import Closeable
from satella.coding.concurrent import PeekableQueue
from satella.coding.structures import DirtyDict
from satella.files import read_in_file

from smokclient.basics import DeviceInfo, Environment
from smokclient.certificate import get_device_info
from smokclient.exceptions import ResponseError
from smokclient.threads.executor import OrderExecutorThread
from smokclient.threads.communicator import OrderGetterThread
from smokclient.pathpoint.pathpoint import Pathpoint


def default_pathpoint(path: str) -> None:
    raise KeyError('Pathpoint does not exist')


class RequestsAPI:
    def __init__(self, device):
        self.environment = device.environment
        self.base_url = device.url
        if self.environment == Environment.STAGING:
            self.cert = read_in_file(device.cert[0], 'utf-8').replace('\n', '\t')
        else:
            self.cert = device.cert

    def get(self, url):
        if self.environment == Environment.STAGING:
            resp = requests.get(self.base_url+url, headers={
                'X-SSL-Client-Certificate': self.cert
            })
        else:
            resp = requests.get(self.base_url+url, cert=self.cert)
        if resp.status_code not in (200, 201):
            raise ResponseError('HTTP %s seen, status is %s' % (resp.status_code,
                                                                resp.json()['status']))
        return resp.json()

    def post(self, url, json_data=None):
        if self.environment == Environment.STAGING:
            resp = requests.post(self.base_url+url, json=json_data, headers={
                'X-SSL-Client-Certificate': self.cert
            })
        else:
            resp = requests.get(self.base_url+url, json=json_data, cert=self.cert)
        if resp.status_code not in (200, 201):
            raise ResponseError('HTTP %s seen, status is %s' % (resp.status_code,
                                                                resp.json()['status']))
        return resp.json()



class SMOKDevice(Closeable):
    """
    A base class for a SMOK device.

    Note that instantiating this object spawns two non-daemon thread. This object must be
    close()d before termination (or __del__eted).

    :param cert: either a path to or a file-like object containing the device certificate
    :param priv_key: either a path to or a file-like object containing the device private key
    """

    def __init__(self, cert: tp.Union[str, io.StringIO],
                 priv_key: tp.Union[str, io.StringIO],
                 unknown_pathpoint_provider: tp.Callable[[str], Pathpoint] = default_pathpoint):
        super().__init__()
        self.unknown_pathpoint_provider = unknown_pathpoint_provider
        self.pathpoints = DirtyDict()
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

        self.api = RequestsAPI(self)

        order_queue = PeekableQueue()

        self.executor = OrderExecutorThread(self, order_queue).start()
        self.getter = OrderGetterThread(self, order_queue).start()

    def close(self) -> None:
        """
        Close the connection, clean up the resources.
        """
        if super().close():
            self.executor.terminate()
            self.getter.terminate()
            if self.temp_file_for_cert:
                os.unlink(self.temp_file_for_cert)
            if self.temp_file_for_key:
                os.unlink(self.temp_file_for_key)
            self.executor.join()
            self.getter.join()

    def get_device_info(self) -> DeviceInfo:
        """
        :return: current device information
        """
        resp = self.api.get('/v1/device')

        return DeviceInfo.from_json(resp)

