Exceptions
==========

The base class for all `smok` exceptions is:

.. autoclass:: smok.exceptions.SMOKClientError
    :members:

smok-client exceptions
----------------------

If there's a problem with your certificate, the following will be raised:

.. autoclass:: smok.exceptions.InvalidCredentials
    :members:

Other notable exceptions are:

.. autoclass:: smok.exceptions.InstanceNotReady

.. autoclass:: smok.exceptions.ResponseError

.. autoclass:: smok.exceptions.OperationFailedError

.. autoclass:: smok.exceptions.OperationFailedReason
    :members:

.. autoclass:: smok.exceptions.NotReadedError
    :members:

NGTT exceptions
---------------

NGTT module also defines some exceptions:

.. autoclass:: ngtt.exceptions.NGTTError

.. autoclass:: ngtt.exceptions.ConnectionFailed

.. autoclass:: ngtt.exceptions.DataStreamSyncFailed

.. autoclass:: ngtt.exceptions.InvalidFrame

However, most probably you won't have to deal with them directly.
