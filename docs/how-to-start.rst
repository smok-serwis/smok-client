How to start
============

First, you will need to obtain a certificate signed by SMOK sp. z o. o. Contact
Piotr Maslanka_ to have you do that. A certificate is
valid either for production_ or for testing_ environments.

.. _Maslanka: mailto:pmaslanka@smok.co

.. _production: https://api.smok.co

.. _testing: http://api.test.smok-serwis.pl

Then you will need to think of what pathpoints your device supports. SMOK sensors are
a server-side construct, so your device thinks in pathpoints. A pathpoint is a single value,
that can be read and written to by SMOK. An example pathpoint would be a single MODBUS register.

You can view the example_, or keep on reading these docs.

.. _example: https://github.com/smok-serwis/smok-client/tree/develop/examples/skylab

What exactly does smok-client handle for me
--------------------------------------------

It handles:

* executing read and write orders
* executing message and wait orders
* handling archiving of pathpoints
* handling scheduled execution of macros
* buffering data about executed macros, opened events and readed data until a contact
  with the server can be made

Starting with some code
-----------------------

First of all, you need to subclass SMOKDevice and define the method
:meth:`~smok.client.SMOKDevice.provide_unknown_pathpoint`.

.. code-block:: python

    from smok.client import SMOKDevice
    from smok.basics import StorageLevel
    from smok.pathpoint import Pathpoint, AdviseLevel, PathpointValueType
    from concurrent.futures import Future

    class MyModbusRegister(Pathpoint):
        def on_read(advise: AdviseLevel) -> Future:
            ...

        def on_write(value: PathpointValueType, advise: AdviseLevel) -> Future:
            ...

    class MyDevice(SMOKDevice):
        def __init__(self):
            super().__init__('path to cert file', 'path to key file',
                             'path to pickle for predicates')

    sd = MyDevice()
    pp = MyModbusRegister('W1', StorageLevel.TREND)
    sd.register_pathpoint(pp)

A very important method of your custom class is
:meth:`~smok.client.SMOKDevice.provide_unknown_pathpoint`. When smok-client encounters
an unknown pathpoint (for example, an order for it was made) it tries to create it.
This method should provide this pathpoint. Note that it doesn't need to provide pathpoints
that you will create and register manually. If a predicate cannot be found, it should raise
`KeyError`.

The pickle for predicates will be used for persisting the state of alarm detectors, aka
:term:`predicate` .

Note that first letter of the pathpoint defines it's type. Allowed are:

.. autoclass:: smok.pathpoint.PathpointType
    :members:

If you need to coerce a value to target pathpoint's type, use the following method:

.. autofunction:: smok.pathpoint.to_type

If the first letter is `r`, then the type of the pathpoint is declared by the second letter.
This pathpoint will be called a :term:`reparse` pathpoint
The rest represents an expression, where other pathpoint are taken in brackets and the resulting
expression is evaluated. This is called a reparse pathpoint, and you don't need to deal directly
with them. You just need to provide the non-reparse, ie. :term:`native` pathpoints.


Both of these calls (ie. `on_read` and `on_write`) must return a Future that will complete
(or fail) when a call is finished. If you failed an operation, you should raise the following inside
your future:

.. autoclass:: smok.exceptions.OperationFailedError
    :members:

A reason has to be given, it is an enum

.. autoclass:: smok.exceptions.OperationFailedReason
    :members:

When you're done, don't forget to close the `SMOKDevice`, since it spawns 3 threads and makes
temporary files with the certificate content, if you provide them not by files, but by file-like
objects.

During invoking the :meth:`smok.pathpoint.Pathpoint.get` you might get the previous exceptions,
but also a new one:

.. autoclass:: smok.exceptions.NotReadedError
    :members:

.. code-block:: python

    sd.close()      # this may block for like 10 seconds

Threads
-------

`SMOKDevice` spawns 3 threads to help it out with it's chores. They are as follows:

* `CommunicatorThread` handles communication with the SMOK server, and following things:
    * reading macros (tasks to be executed in the future)
    * synchronizes :ref:`BAOBs`
    * fetches orders to execute on `OrderExecutorThread`
    * synchronizes pathpoints and sensors
    * synchronizes and executes :ref:`predicates`
* `ArchivingAndMacroThread` takes care of reading the pathpoints that are archived,
  about executing macros, and synchronizes the metadata in the background.
* `OrderExecutorThread` handles the loop executing orders.
* `LogPublisherThread` handles publishing your logs to the SMOK server

Nearly all of the callbacks that you provide will be called in the context of one of aforementioned
threads. It will be documented which thread calls your callback.

List of basic classes
=====================

SMOKDevice
----------
.. autoclass:: smok.client.SMOKDevice
    :members:

Pathpoint
---------
.. autoclass:: smok.pathpoint.Pathpoint
    :members:

.. autoclass:: smok.pathpoint.ReparsePathpoint
    :members:

Enums
-----
.. autoclass:: smok.pathpoint.AdviseLevel
    :members:


.. autoclass:: smok.basics.StorageLevel
    :members:


.. autoclass:: smok.basics.Environment
    :members:

Executing orders
----------------

If you want to read given pathpoint, just do the following:

.. code-block:: python

    read_order = pathpoint.read()
    sd.execute(read_order)

Note that any :class:`smok.pathpoint.orders.Section` is also a perfectly valid `Future`, so
you may cancel it and wait for it's result:

.. code-block:: python

    read_order.result()

Sadly, the completion of a Section just means that all orders have been executed, it bears
no relevance **how** they completed. You may even cancel it:

.. code-block:: python

    if read_order.cancel():
        print('Successfully cancelled')

Custom order-execution loop
---------------------------

If you want to write a custom order-execution loop, just override
:meth:`smok.client.SMOKDevice.execute_section`. It will accept a single argument of
:class:`~smok.pathpoint.orders.Section`, about which you can read up in :ref:`orders`.

You will also need to provide a method
:meth:`smok.client.SMOKDevice.sync_sections` to block until all orders from previous section
have been completed.

Both of these methods will be called by the `OrderExecutorThread`.
