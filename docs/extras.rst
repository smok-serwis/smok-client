Extras
======

If you wish to extend the functionality of smok-client somehow, here's how you can do it.

Most options are, for this time, geared towards extended work in an Internet-less environment.

Note that if documentation says that client threads can invoke these routines, you should make them
as threadsafe as feasible for you.

BAOB storage
------------
BAOBs are essentially similar to metadata, except for being versioned monotonically
and being composed of bytes instead of characters.

If you want your BAOBs to persist restarts, feel free to implement following class:

.. autoclass:: smok.extras.BaseBAOBDatabase
    :members:

.. autoclass:: smok.extras.BAOBDigest
    :members:

Sadly, since BAOB files can be downloaded each time the application starts, you're on your own.

Sensor storage
--------------

If you wish to persist your sensor definition across restarts, feel free to implement the following:


.. autoclass:: smok.extras.BaseSensorDatabase
    :members:

If you need quickly a persisting pathpoint database, try

.. autoclass:: smok.extras.PicklingSensorDatabase


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
