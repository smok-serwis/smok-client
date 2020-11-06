import os
import ssl
import typing as tp
import io
import tempfile


import pkg_resources

from smokclient.certificate import get_device_info


class SMOKDevice:
    """
    A base class for a SMOK device

    :param cert: either a path to or a file-like object containing the device certificate
    :param priv_key: either a path to or a file-like object containing the device private key
    """
    __slots__ = ('temp_file_for_cert', 'temp_file_for_key', 'device_id',
                 'environment', 'ssl_context', 'url')

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

        self.ssl_context = ssl.create_default_context()

        with open(cert, 'rb') as fin:
            cert_data = fin.read()

        self.device_id, self.environment = get_device_info(cert_data)
        if self.environment == 0:
            self.url = 'https://api.smok.co/'
        elif self.environment == 1:
            self.url = 'http://api.test.smok-serwis.pl/'

    def __del__(self) -> None:
        if self.temp_file_for_cert:
            os.unlink(self.temp_file_for_cert)
        if self.temp_file_for_key:
            os.unlink(self.temp_file_for_key)


