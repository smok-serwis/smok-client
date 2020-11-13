Predicates
==========

Predicate are a way for the device to report any anomalies on it. It works by means of the
userland querying `smok-client` about value of given sensors, and responding properly, by
opening an event (alarm condition) or closing it.

Sensors
-------

Since sensors are an server-side construct, but predicates make use of them, here's a section about
sensors.

There's a way to access the value of a sensor. Where SMOK would represent the value of a
sensor either by a JSONable value, or by a value and it's units (via pint_), `smok-client`
does away with units, and returns sensor values only as JSONable values.

.. _pint: https://pint.readthedocs.io/

Let's look at the sensor class:

.. autoclass:: smokclient.sensor.Sensor
    :members:

And a type of it's value:

.. autodata:: smokclient.sensor.SensorValueType

:attr:`~smokclient.sensor.Sensor.fqts` is the basic of the sensor naming system. Each name
is a set of words, separated by a whitespace. `fqts` is these words split by a space, sorted and
then joined, ensuring that the names stay unique and not depend on order (since a set has no order).

The correct operation to standarize a sensor's name is below:

.. autofunction:: smokclient.sensor.fqtsify

.. note:: **Why tags?**
          Most SCADA system order their sensors in a hierarchical manner. SMOK does not use
          that, preferring for the far more elastic tag system, since it allows to organise the user in
          arbitrary-dimensional hierarchies.

You are more than welcome to make direct use of Sensors, especially when facing output to client.
It makes more sense to use :class:`~smokclient.sensor.Sensor` s for that,
because :class:`~smokclient.sensor.Sensor` s represent a concept, while
pathpoint represents a single endpoint on the client.

Predicates
----------

You work with predicates in such a way, that you register a bunch of classes
to handle provided statistics. A predicate is defined on-server, and smok-client will
take care to instantiate your classes with the proper data.
Let's see how a predicate is built:

.. autoclass:: smokclient.predicate.BaseStatistic
    :members:

.. autoclass:: smokclient.predicate.Event
    :members:

.. autoclass:: smokclient.predicate.Color
    :members:

Example:

::
    class MyStatistic(BaseStatistic):
        statistic_name = 'my'

        def on_tick(self):
            sen = self.device.get_sensor('value')
            if sen.get()[1] > 0 and self.state is None:
                self.state = self.open_event('Hello world!', Color.RED)
            elif self.state is not None and sen.get()[1] == 0:
                self.close_event(self.state)
                self.state = None

    sd.register_statistic(MyStatistic)

Silencing
---------

During specified times, the user does not want to bother him with the predicate's alerts.
Following classes are given as arguments to your constructor:

.. autoclass:: smokclient.predicate.Time
    :members:

.. autoclass:: smokclient.predicate.DisabledTime
    :members:

Opening, closing events and state
---------------------------------

Every predicate has a magic property of :attr:`~smokclient.predicate.BaseStatistic.state`.
It will be restored between calls to :meth:`~smokclient.predicate.BaseStatistic.on_tick`
and saved after it. You best store the :class:`~smokclient.predicate.Event` that you're created
via :meth:`~smokclient.predicate.BaseStatistic.open_event`.

You open new events via :meth:`~smokclient.predicate.BaseStatistic.open_event`
and close them with :meth:`~smokclient.predicate.BaseStatistic.close_event`. Example code could look like:

::
    from satella.coding import silence_excs
    from smokclient.predicate import BaseStatistic, Color, Event
    from smokclient.exceptions import OperationFailedError

    class CustomPredicate(BaseStatistic):
        """
        A predicate that watches for
        """
        statistic_name = 'test'

        @silence_excs(KeyError, OperationFailedError)
        def on_tick(self) -> None:
            sensor = self.device.get_sensor('value')
            self.device.execute(sensor.read())
            ts, v = sensor.get()
            if v == 10 and self.state is None:
                self.state = self.open_event('Value is equal to 10', Color.RED)     # type: Event
            elif v != 10 and self.state is not None:
                self.close_event(self.state)
                self.state = None

    sd.register_statistic(CustomPredicate)
