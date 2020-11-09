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

In that case, you should write:

::

    from smokclient.client import SMOKDevice
    from smokclient.basics import StorageLevel
    from smokclient.pathpoint import Pathpoint, AdviseLevel, PathpointValueType
    from concurrent.futures import Future

    sd = SMOKDevice('path to cert file', 'path to key file')

    class MyModbusRegister(Pathpoint):
        def on_read(advise: AdviseLevel) -> Future:
            ...

        def on_write(value: PathpointValueType, advise: AdviseLevel) -> Future:
            ...

    pp = MyModbusRegister('W1', StorageLevel.TREND)
    sd.register_pathpoint(pp)

Both of these calls (ie. `on_read` and `on_write`) must return a Future that will complete
(or fail) when a call is finished. If you failed an operation, you should raise the following inside
your future:

.. autoclass:: smokclient.exceptions.OperationFailedError

A reason has to be given, it is an enum

.. autoclass:: smokclient.exceptions.OperationFailedReason
    :members:

When you're done, don't forget to close the `SMOKDevice`, since it spawns 3 threads!

::

    sd.close()      # this may block for like 10 seconds


Class droplist
==============

.. autoclass:: smokclient.client.SMOKDevice
    :members:

.. autoclass:: smokclient.pathpoint.Pathpoint
    :members:

.. autoclass:: smokclient.pathpoint.AdviseLevel
    :members:

.. autoclass:: smokclient.basics.StorageLevel
    :members:
