Exceptions
==========

The base class for all `smok` exceptions is:

.. autoclass:: smok.exceptions.SMOKClientError
    :members:

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
