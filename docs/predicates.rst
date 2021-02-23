Predicates
==========

.. _predicates:

Predicate are a way for the device to report any anomalies on it. It works by means of the
userland querying `smok-client` about value of given sensors, and responding properly, by
opening an event (alarm condition) or closing it.

Predicates
----------

You work with predicates in such a way, that you register a bunch of classes
to handle provided statistics. A predicate is defined on-server, and smok-client will
take care to instantiate your classes with the proper data.
Let's see how a predicate is built:

.. autoclass:: smok.predicate.BaseStatistic
    :members:

.. autoclass:: smok.predicate.Event
    :members:

.. autoclass:: smok.predicate.Color
    :members:

Example:

.. code-block:: python

    class MyStatistic(BaseStatistic):
        statistic_name = 'my'

        def on_tick(self):
            sen = self.device.get_sensor('value')
            if sen.get()[1] > 0 and self.state is None:
                self.state = self.open_event('Hello world!', Color.RED)
            elif self.state is not None and sen.get()[1] == 0:
                self.close_event(self.state)
                self.state = None

    sd.register_statistic(MyStatistic, lambda stat, cfg: stat == 'my_statistic')

Silencing
---------

During specified times, the user does not want to bother him with the predicate's alerts.
Following classes are given as arguments to your constructor:

.. autoclass:: smok.predicate.Time
    :members:

.. autoclass:: smok.predicate.DisabledTime
    :members:

Opening, closing events and state
---------------------------------

Every predicate has a magic property of :attr:`~smok.predicate.BaseStatistic.state`.
It will be restored between calls to :meth:`~smok.predicate.BaseStatistic.on_tick`
and saved after it. You best store the :class:`~smok.predicate.Event` that you're created
via :meth:`~smok.predicate.BaseStatistic.open_event`.

You open new events via :meth:`~smok.predicate.BaseStatistic.open_event`
and close them with :meth:`~smok.predicate.BaseStatistic.close_event`. Example code could look like:

.. code-block:: python

    from satella.coding import silence_excs
    from smok.predicate import BaseStatistic, Color, Event
    from smok.exceptions import OperationFailedError

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

    sd.register_statistic(CustomPredicate, lambda stat_name, cfg: stat_name == 'my_statistic')

Beware, :term:`point event`s cannot be closed as they do not span a period and are created closed.

Registrations
-------------

A :meth:`~smok.client.SMOKDevice.register_statistic` returns objects of following type:

.. autoclass:: smok.predicate.registration.StatisticRegistration
    :members:
