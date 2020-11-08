__all__ = ['SMOKClientError', 'InvalidCredentials', 'ResponseError',
           'OperationFailedReason', 'OperationFailedError']

import enum


class SMOKClientError(Exception):
    """Base class for all exceptions thrown by SMOK client"""


class InvalidCredentials(SMOKClientError):
    """
    The certificate files that you provided were invalid
    """


class ResponseError(SMOKClientError):
    """
    Server replied with a wrong code
    """
    def __str__(self) -> str:
        return 'ResponseError(%s, "%s")' % (self.status_code, self.status)

    def __init__(self, status_code: int, status: str):
        self.status_code = status_code
        self.status = status


class OperationFailedReason(enum.Enum):
    # The target device responded with a malformed protocol frame
    MALFORMED = 'malformed'
    # The target device did not respond within given time
    TIMEOUT = 'timeout'
    # The target device responded correctly, but told us that this pathpoint is bogus
    INVALID = 'invalid'


class OperationFailedError(SMOKClientError):
    """
    Raised by the pathpoint's on_read and on_write futures when the operation fails
    """
    def __init__(self, reason: OperationFailedReason):
        self.reason = reason
