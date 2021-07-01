import logging
import typing as tp

import pkg_resources
from OpenSSL import crypto
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from pyasn1.codec.der.decoder import decode
from pyasn1.error import PyAsn1Error
from satella.coding import reraise_as
from satella.coding.structures import Singleton
from satella.files import read_in_file

from smok.basics import Environment
from smok.exceptions import InvalidCredentials

logger = logging.getLogger(__name__)

DEVICE_ID = x509.ObjectIdentifier('1.3.6.1.4.1.55338.0.0')
ENVIRONMENT = x509.ObjectIdentifier('1.3.6.1.4.1.55338.0.1')
# noinspection PyProtectedMember
x509.oid._OID_NAMES[DEVICE_ID] = 'DeviceID'
# noinspection PyProtectedMember
x509.oid._OID_NAMES[ENVIRONMENT] = 'Environment'


def get_root_cert() -> bytes:
    """
    :return: the bytes sequence for SMOK's master CA certificate
    """
    ca_file = pkg_resources.resource_filename('smok', 'certs/root.crt', )
    return read_in_file(ca_file)


def get_rapid_ca_cert() -> bytes:
    """
    :return: the bytes sequence for a PEM-encoded RAPID host signing CA
    """


def get_dev_ca_cert() -> bytes:
    """
    :return: the bytes sequence for SMOK's device signing CA
    """
    ca_file = pkg_resources.resource_filename('smok', 'certs/dev.crt', )
    return read_in_file(ca_file)


@Singleton
class DevRootCertificateStore:
    __slots__ = ('store',)

    def add_certificate(self, name: str):
        ca_file = pkg_resources.resource_filename('smok', 'certs/%s' % (name,))
        cert_pem_data = read_in_file(ca_file)
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_pem_data)
        self.store.add_cert(cert)

    def __init__(self):
        self.store = crypto.X509Store()
        self.add_certificate('root.crt')
        self.add_certificate('dev.crt')
        self.add_certificate('rapid.crt')


DevRootCertificateStore()


def check_if_trusted(cert_data: bytes) -> bool:
    try:
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)
    except crypto.Error as e:
        raise InvalidCredentials('problem loading certificate - certificate is invalid') from e
    store_ctx = crypto.X509StoreContext(DevRootCertificateStore().store, cert)
    try:
        store_ctx.verify_certificate()
        return True
    except crypto.Error:
        return False


def get_device_info(cert_data: bytes) -> tp.Tuple[str, Environment]:
    try:
        cert = x509.load_pem_x509_certificate(cert_data, default_backend())
    except ValueError as e:
        raise InvalidCredentials('Error unserializing certificate') from e

    try:
        device_asn1 = cert.extensions.get_extension_for_oid(DEVICE_ID).value.value
    except x509.extensions.ExtensionNotFound as e:
        return InvalidCredentials('DEVICE_ID not found in cert: %s' % (e,))

    try:
        device_id = str(decode(device_asn1)[0])
    except (PyAsn1Error, IndexError) as e:
        return InvalidCredentials('error during decoding DEVICE_ID: %s' % (e,))

    try:
        environment_asn1 = cert.extensions.get_extension_for_oid(ENVIRONMENT).value.value
    except x509.extensions.ExtensionNotFound as e:
        raise InvalidCredentials(str(e))

    try:
        environment = int(decode(environment_asn1)[0])
    except (PyAsn1Error, IndexError, TypeError) as e:
        raise InvalidCredentials('error during decoding environment: %s' % (e,)) from e
    except ValueError as e:
        raise InvalidCredentials('unrecognized environment: %s' % (e,)) from e

    with reraise_as(ValueError, InvalidCredentials):
        return device_id, Environment(environment)
