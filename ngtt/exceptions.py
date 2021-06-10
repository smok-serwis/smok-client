class NGTTError(Exception):
    pass


class ConnectionFailed(NGTTError):
    """
    :ivar is_due_to_no_internet: was this error caused by the internet not being there?
    """
    def __init__(self, is_due_to_no_internet: bool = False):
        self.is_due_to_no_internet = is_due_to_no_internet


class DataStreamSyncFailed(NGTTError):
    pass


class InvalidFrame(NGTTError):
    pass
