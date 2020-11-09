import os
import typing as tp
import io
import tempfile

from satella.coding import Closeable
from satella.coding.concurrent import PeekableQueue
from satella.coding.structures import DirtyDict

from smokclient.client.api import RequestsAPI
from smokclient.basics import DeviceInfo, Environment, StorageLevel
from smokclient.client.certificate import get_device_info
from smokclient.pathpoint.data_sync_dict import DataSyncDict
from smokclient.threads import OrderExecutorThread, CommunicatorThread, ArchivingAndMacroThread
from smokclient.pathpoint.pathpoint import Pathpoint


def default_pathpoint(path: str, storage_level: StorageLevel) -> None:
    raise KeyError('Pathpoint does not exist')


class SMOKDevice(Closeable):
    """
    A base class for a SMOK device.

    Note that instantiating this object spawns two non-daemon thread. This object must be
    close()d before termination (or __del__eted).

    :param cert: either a path to or a file-like object containing the device certificate
    :param priv_key: either a path to or a file-like object containing the device private key
    :param unknown_pathpoint_provider: a callable that is called with two arguments:
        pathpoint name and pathpoint storage level. It is supposed to return a Pathpoint
        object, or raise KeyError if it doesn't exist.
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
        data_to_sync = DataSyncDict()

        self.arch_and_macros = ArchivingAndMacroThread(self, order_queue).start()
        self.executor = OrderExecutorThread(self, order_queue, data_to_sync).start()
        self.getter = CommunicatorThread(self, order_queue, data_to_sync).start()

    def register_pathpoint(self, pp: Pathpoint) -> None:
        self.pathpoints[pp.name] = pp

    def close(self) -> None:
        """
        Close the connection, clean up the resources.
        """
        if super().close():
            self.executor.terminate()
            self.getter.terminate()
            self.arch_and_macros.terminate()
            if self.temp_file_for_cert:
                os.unlink(self.temp_file_for_cert)
            if self.temp_file_for_key:
                os.unlink(self.temp_file_for_key)
            self.executor.join()
            self.getter.join()
            self.arch_and_macros.join()

    def get_device_info(self) -> DeviceInfo:
        """
        :return: current device information
        """
        resp = self.api.get('/v1/device')

        return DeviceInfo.from_json(resp)

