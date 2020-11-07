__all__ = ['SMOKClientError', 'InvalidCredentials', 'ResponseError']


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
