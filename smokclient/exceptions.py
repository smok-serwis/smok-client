class SMOKClientError(Exception):
    """Base class for all exceptions thrown by SMOK client"""


class InvalidCredentials(SMOKClientError):
    """
    The certificate files that you provided were invalid
    """

__all__ = ['SMOKClientError', 'InvalidCredentials']
