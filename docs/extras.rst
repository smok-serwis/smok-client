Extras
======

If you wish to extend the functionality of smok-client somehow, here's how you can do it.

Pathpoint value storage
-----------------------

If you want to store your pathpoint values in a way that would survive restarts, just define both
classes:

.. autoclass:: smokclient.extras.BasePathpointDatabase
    :members:

.. autoclass:: smokclient.extras.BaseDataToSynchronize
    :members:

And create an instance of `BasePathpointDatabase` and feed it to argument
of :class:`~smokclient.client.SMOKDevice`.

If you need quickly a persisting pathpoint database, try

.. autoclass:: smokclient.extras.PicklingPathpointDatabase

It does not however provide for archives.

Event storage
-------------

.. autoclass:: smokclient.extras.BaseEventSynchronization
    :members:

.. autoclass:: smokclient.extras.BaseEventDatabase
    :members:


If you need quickly a pickling database, try

.. autoclass:: smokclient.extras.PicklingEventDatabase
    :members:
