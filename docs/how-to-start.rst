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

First of all, you need to subclass SMOKDevice and define the method
:meth:`~smokclient.client.SMOKDevice.provide_unknown_pathpoint`.

::

    from smokclient.client import SMOKDevice
    from smokclient.basics import StorageLevel
    from smokclient.pathpoint import Pathpoint, AdviseLevel, PathpointValueType
    from concurrent.futures import Future

    class MyModbusRegister(Pathpoint):
        def on_read(advise: AdviseLevel) -> Future:
            ...

        def on_write(value: PathpointValueType, advise: AdviseLevel) -> Future:
            ...

    class MyDevice(SMOKDevice):
        def __init__(self):
            super().__init__('path to cert file', 'path to key file')

    sd = MyDevice()
    pp = MyModbusRegister('W1', StorageLevel.TREND)
    sd._register_pathpoint(pp)

A very important method of your custom class is
:meth:`~smokclient.client.SMOKDevice.provide_unknown_pathpoint`. When smok-client encounters
an unknown pathpoint (for example, an order for it was made) it tries to create it.
This method should provide this pathpoint. Note that it doesn't need to provide pathpoints
that you will create and register manually. If a predicate cannot be found, it should raise
`KeyError`.

Note that first letter of the pathpoint defines it's type. Allowed are:

.. autoclass:: smokclient.pathpoint.PathpointType
    :members:

If you need to coerce a value to target pathpoint's type, use the following method:

.. autofunction:: smokclient.pathpoint.to_type

If the first letter is `r`, then the type of the pathpoint is declared by the second letter.
This pathpoint will be called a :term:`reparse` pathpoint
The rest represents an expression, where other pathpoint are taken in brackets and the resulting
expression is evaluated. This is called a reparse pathpoint, and you don't need to deal directly
with them. You just need to provide the non-reparse, ie. :term:`native` pathpoints.


Both of these calls (ie. `on_read` and `on_write`) must return a Future that will complete
(or fail) when a call is finished. If you failed an operation, you should raise the following inside
your future:

.. autoclass:: smokclient.exceptions.OperationFailedError
    :members:

A reason has to be given, it is an enum

.. autoclass:: smokclient.exceptions.OperationFailedReason
    :members:

When you're done, don't forget to close the `SMOKDevice`, since it spawns 3 threads and makes
temporary files with the certificate content, if you provide them not by files, but by file-like
objects.

During invoking the :meth:`smokclient.pathpoint.Pathpoint.get` you might get the previous exceptions,
but also a new one:

.. autoclass:: smokclient.exceptions.NotReadedError
    :members:

::

    sd.close()      # this may block for like 10 seconds

Threads
-------

`SMOKDevice` spawns 3 threads to help it out with it's chores. They are as follows:

* `CommunicatorThread` handles communication with the SMOK server
* `ArchivingAndMacroThread` takes care of reading the pathpoints that are archived and
    about executing macros
* `OrderExecutorThread` handles the loop executing orders.

Nearly all of the callbacks that you provide will be called in the context of one of aforementioned
threads. It will be documented which thread calls your callback.

Class droplist
==============

SMOKDevice
----------
.. autoclass:: smokclient.client.SMOKDevice
    :members:

Pathpoint
---------
.. autoclass:: smokclient.pathpoint.Pathpoint
    :members:

Enums
-----
.. autoclass:: smokclient.pathpoint.AdviseLevel
    :members:


.. autoclass:: smokclient.basics.StorageLevel
    :members:


.. autoclass:: smokclient.basics.Environment
    :members:


DTO's
-----
.. autoclass:: smokclient.basics.DeviceInfo
    :members:


.. autoclass:: smokclient.basics.SlaveDeviceInfo
    :members:


.. autodata:: smokclient.pathpoint.PathpointValueType


.. autodata:: smokclient.pathpoint.ValueOrExcept
