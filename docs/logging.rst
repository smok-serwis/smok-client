Logging
=======

smok can also intercept your Python logs and send them to the server.

First you should create a `SMOKDevice` instance, then create an instance of
and register this handler:

.. autoclass:: smok.logging.SMOKLogHandler

Then you should add it to your list of handlers:

.. code-block:: python

    handler = SMOKLogHandler(sd, 'device')
    logger = logging.getLogger()
    logger.addHandler(handler)


.. note:: Service name is used to distinguish multiple processes running as the same device.

.. note:: Logging events are not stored for later submission. Either they are submitted at the moment,
    or they are lost forever.
