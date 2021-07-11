import enum
import typing as tp

__all__ = ['SMOKClientError', 'InvalidCredentials', 'ResponseError',
           'OperationFailedReason', 'OperationFailedError',
           'NotReadedError', 'InstanceNotReady',
           'UnavailableError']

from satella.coding.typing import Number
from satella.time import time_ms


class SMOKClientError(Exception):
    """Base class for all exceptions thrown by SMOK client"""


class InvalidCredentials(SMOKClientError):
    """
    The certificate files that you provided were invalid
    """


class InstanceNotReady(SMOKClientError):
    """
    Some operation must be done before you can call that method
    """


class UnavailableError(SMOKClientError):
    """
    The client was started in a mode that does not support your request, ie. requesting
    a BAOB while starting client with
    """


class ResponseError(SMOKClientError):
    """
    Server replied with a wrong code or didn't reply at all.
    """

    def __str__(self) -> str:
        return 'ResponseError(%s, "%s")' % (self.status_code, self.status)

    def __init__(self, status_code: tp.Optional[int] = 599, status: str = ''):
        self.status_code = status_code
        self.status = status

    def is_no_link(self) -> bool:
        """
        :return: whether this fault happened due to link failing
        """
        return self.status_code == 599

    def is_clients_fault(self) -> bool:
        """
        :return: whether this is our fault, or server's/connection's fault
        """
        return self.status_code // 100 == 4


class OperationFailedReason(enum.Enum):
    MALFORMED = 'malformed'  #: The device responded with a malformed protocol frame
    TIMEOUT = 'timeout'  #: The device did not respond within given time
    INVALID = 'invalid'  #: The device responded OK, but told us that this pathpoint is bogus
    TYPE = 'type'  #: There was an error with the typing of the value


class OperationFailedError(SMOKClientError):
    """
    Raised by the pathpoint's on_read and on_write futures when the operation fails

    :ivar reason: reason of failure, or None if just not readed
    :ivar timestamp: timestamp of failure in milliseconds
    """

    def __init__(self, reason: OperationFailedReason = OperationFailedReason.TIMEOUT,
                 timestamp: tp.Optional[Number] = None):
        self.reason = reason
        self.timestamp = timestamp or time_ms()


class NotReadedError(OperationFailedError):
    """
    The value is not available, due to it having not been yet read.

    Note that this is invalid to return in read handling futures!

    :ivar timestamp: timestamp of failure in milliseconds
    """

    def __init__(self, timestamp: tp.Optional[float] = None):
        super().__init__(None, timestamp)
