Metadata
========

Metadata is a key-value (string-string) store attached to a device.

Support for metadata is the :code:`metadata` property of :class:`~rapid.client.SMOKDevice`.

It contains an instance of the following:

.. autoclass:: smok.metadata.PlainMetadata
    :members:

It supports :code:`__getitem__`, :code:`__setitem__` and :code:`__delitem__`. It does not support
:code:`__len__` and :code:`__iter__`.


.. note:: Right now the SMOK API only allows access to plain metadata.
