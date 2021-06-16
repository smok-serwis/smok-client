from smok.exceptions import SMOKClientError


class NGTTError(SMOKClientError):
    """Base class for NGTT exceptions"""
    pass


class ConnectionFailed(NGTTError):
    """
    The request failed due to a problem with connection

    :ivar is_due_to_no_internet: was this error caused by the internet not being there?
    """

    def __init__(self, is_due_to_no_internet: bool = False, *args):
        super().__init__(*args)
        self.is_due_to_no_internet = is_due_to_no_internet


class DataStreamSyncFailed(NGTTError):
    """
    Server declined to sync data, as it's invalid.
    """


class InvalidFrame(NGTTError):
    """
    An invalid frame has been sent over the wire
    """
