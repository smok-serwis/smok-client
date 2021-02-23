Extras
======

.. _extras:

If you wish to extend the functionality of smok-client somehow, here's how you can do it.

Most options are, for this time, geared towards extended work in an Internet-less environment.

Note that if documentation says that client threads can invoke these routines, you should make them
as threadsafe as feasible for you.

Predicate database
------------------

Implement a class with this interface:

.. autoclass:: smok.extras.BasePredicateDatabase
    :members:

If you need a quick pickling solution, use:

.. autoclass:: smok.extras.PicklingPredicateDatabase
    :members:

Sensor writes database
----------------------

In a SCADA system it is very important to know who's been changing what. SMOK allows you to
register sensor writes to send to the cloud. However, if you would like them to persist
a reboot, override this:

.. autoclass:: smok.extras.BaseSensorWriteSynchronization
    :members:

.. autoclass:: smok.extras.BaseSensorWriteDatabase
    :members:

If you need something which persists the data, but isn't too fast itself, try:

.. autoclass:: smok.extras.PicklingSensorWriteDatabase
    :members:

Archive database
----------------

Lists of pathpoints to be archived also need to persist in case of restart. You need to
implement the following:

.. autoclass:: smok.extras.BaseArchivesDatabase
    :members:

In case you want a fast solution, there's also

.. autoclass:: smok.extras.PicklingArchivesDatabase
    :members:

BAOB storage
------------
BAOBs are essentially similar to metadata, except for being versioned monotonically
and being composed of bytes instead of characters.

If you want your BAOBs to persist restarts, feel free to implement following class:

.. autoclass:: smok.extras.BaseBAOBDatabase
    :members:

.. autoclass:: smok.extras.BAOBDigest
    :members:

If you want a quick database that persists restarts, take a look at:

.. autoclass:: smok.extras.PicklingBAOBDatabase
    :members:

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

If you don't care about events, you can also use

.. autoclass:: smok.extras.NullEventDatabase
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

Retrieving SMOK certificates
----------------------------

.. autofunction:: smok.client.get_root_cert

.. autofunction:: smok.client.get_dev_ca_cert
