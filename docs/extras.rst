Extras
======

If you wish to extend the functionality of smok-client somehow, here's how you can do it.

Pathpoint value storage
-----------------------

If you want to store your pathpoint values in a way that would survive restarts, just define both
classes:

.. autoclass:: smok.extras.BasePathpointDatabase
    :members:

.. autoclass:: smok.extras.BaseDataToSynchronize
    :members:

And create an instance of `BasePathpointDatabase` and feed it to argument
of :class:`~smok.client.SMOKDevice`.

If you need quickly a persisting pathpoint database, try

.. autoclass:: smok.extras.PicklingPathpointDatabase

It does not however provide for archives.

Event storage
-------------

.. autoclass:: smok.extras.BaseEventSynchronization
    :members:

.. autoclass:: smok.extras.BaseEventDatabase
    :members:


If you need quickly a pickling database, try

.. autoclass:: smok.extras.PicklingEventDatabase
    :members:

Macro storage
-------------

.. autoclass:: smok.extras.BaseMacroDatabase
    :members:

If you need quickly a pickling database, try

.. autoclass:: smok.extras.PicklingMacroDatabase
    :members:

Metadata store
--------------

.. autoclass:: smok.extras.BaseMetadataDatabase
    :members:

If you need quickly a pickling database, try

.. autoclass:: smok.extras.PicklingMetadataDatabase
    :members:
