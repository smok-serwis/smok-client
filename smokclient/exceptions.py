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
    def __str__(self) -> str:
        return 'ResponseError(%s, "%s")' % (self.status_code, self.status)

    def __init__(self, status_code: int, status: str):
        self.status_code = status_code
        self.status = status
