Sensors
=======

Since :term:`sensor`s are an server-side construct, but predicates make use of them, here's a section about
sensors.

Note that you can't define any sensors yourself and must rely on the server to do that.

There's a way to access the value of a sensor. Where SMOK would represent the value of a
sensor either by a JSONable value, or by a value and it's units (via pint_), `smok-client`
does away with units, and returns sensor values only as JSONable values. The unit part is simply
stripped from the value.

.. _pint: https://pint.readthedocs.io/

Let's look at the sensor class:

.. autoclass:: smok.sensor.Sensor
    :members:

And a type of it's value:

.. autodata:: smok.sensor.SensorValueType

:attr:`~smok.sensor.Sensor.fqts` is the basic of the sensor naming system. Each name
is a set of words, separated by a whitespace. `fqts` is these words split by a space, sorted and
then joined, ensuring that the names stay unique and not depend on order (since a set has no order).

The correct operation to standarize a sensor's name is below:

.. autofunction:: smok.sensor.fqtsify

.. note:: **Why tags?**
          Most SCADA system order their sensors in a hierarchical manner. SMOK does not use
          that, preferring for the far more elastic tag system, since it allows to organise the user in
          arbitrary-dimensional hierarchies.

You are more than welcome to make direct use of Sensors, especially when facing output to client.
It makes more sense to use :class:`~smok.sensor.Sensor` s for that,
because :class:`~smok.sensor.Sensor` s represent a concept, while
pathpoint represents a single endpoint on the client.

Sensor types
------------

Every sensor has a type. Type describes how to convert values from pathpoints to sensor and vice
versa. Base class for types is:

.. autoclass:: smok.sensor.types.BasicType
    :members:

Other common types are:

.. autoclass:: smok.sensor.types.NumericType
    :members:

.. autoclass:: smok.sensor.types.UnicodeType
    :members:

Logging writes
--------------

In order to log a write, you must construct an instance of following:

.. autoclass:: smok.sensor.SensorWriteEvent
    :members:

And pass it as an argument to :meth:`~smok.client.SMOKDevice.log_sensor_write`.
