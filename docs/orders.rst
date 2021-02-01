Issuing orders
==============

.. _orders:

Orders are dispatched in so-called sections. Section is a bunch of orders that
can be thought to execute in parallel.

.. autoclass:: smok.pathpoint.Section
    :members:

.. autoclass:: smok.pathpoint.ReadOrder
    :members:

.. autoclass:: smok.pathpoint.WriteOrder
    :members:

.. autoclass:: smok.pathpoint.WaitOrder
    :members:

.. autoclass:: smok.pathpoint.MessageOrder
    :members:

Note that all of the:

* :meth:`smok.pathpoint.Pathpoint.read`
* :meth:`smok.pathpoint.Pathpoint.write`
* :meth:`smok.sensor.Sensor.read`
* :meth:`smok.sensor.Sensor.write`

Will return you a :class:`smok.pathpoint.Section` that represents what needs to be done
in order to carry out your command. You need to execute
with :meth:`smok.client.SMOKDevice.execute` in order for them to take any effect.
