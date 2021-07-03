import logging
import time
import typing as tp
import weakref
from abc import ABCMeta, abstractmethod
from datetime import datetime
from satella.coding.structures import OmniHashableMixin

from smok.predicate.event import Color, Event

logger = logging.getLogger(__name__)


class Time(OmniHashableMixin):
    """
    A representation of a time during a weekday

    :ivar day_of_week: day of week, as per ISO 8601
    :ivar hour: a hour, according to a 24-hour clock
    :ivar minute: a minute
    """
    _HASH_FIELDS_TO_USE = ('day_of_week', 'hour', 'minute')
    __slots__ = ('day_of_week', 'hour', 'minute')

    def __init__(self, day_of_week: int, hour: int, minute: int):
        self.day_of_week = day_of_week
        self.hour = hour
        self.minute = minute

    @classmethod
    def from_json(cls, dct: dict) -> 'Time':
        return Time(dct['day'], dct['hour'], dct['minute'])

    def to_tuple(self) -> tp.Tuple[int, int, int]:
        return self.day_of_week, self.hour, self.minute


class DisabledTime(OmniHashableMixin):
    """
    Class marking a period during a week

    :ivar start: when this period starts
    :ivar stop: when this period stops
    """
    _HASH_FIELDS_TO_USE = ('start', 'stop')
    __slots__ = ('start', 'stop')

    def __init__(self, start: Time, stop: Time):
        self.start = start
        self.stop = stop

    @classmethod
    def from_json(cls, x: dict) -> 'DisabledTime':
        return DisabledTime(Time.from_json(x['start']), Time.from_json(x['stop']))

    def is_in_time(self, t: datetime) -> bool:
        """
        Check whether provided time is inside the range of this silencing period.

        :return: True if the time is inside
        """
        return self.start.to_tuple() <= (t.isoweekday(), t.hour, t.minute) \
               <= self.stop.to_tuple()


class BaseStatistic(metaclass=ABCMeta):
    """
    Base class for your own predicates.

    :ivar device: a weak reference to the SMOKDevice
    :ivar predicate_id: ID of the predicate
    :ivar verbose_name: Human-readable name of this predicate
    :ivar silencing: periods during which the predicate shouldn't generate alerts
    :ivar configuration: a dictionary containing the predicate's configuration
    :ivar group: notification group
    :ivar state: state of the predicate, persisted between calls (picklable)
    :cvar statistic_name: name of this statistic
    """

    def __init__(self, device: 'SMOKDevice', predicate_id: str, verbose_name: str,
                 silencing: tp.List[DisabledTime],
                 configuration: tp.Optional[dict], statistic: tp.Optional[str] = None,
                 group: str = 'B', state=None, **kwargs):
        self.device = weakref.proxy(device)
        self.predicate_id = predicate_id
        self.verbose_name = verbose_name
        self.silencing = silencing
        self.configuration = configuration
        self.statistic = statistic
        self.group = group
        self.state = state
        self.kwargs = kwargs

    def to_kwargs(self) -> dict:
        r = {'group': self.group, 'predicate_id': self.predicate_id,
             'verbose_name': self.verbose_name, 'silencing': self.silencing,
             'configuration': self.configuration, 'statistic': self.statistic,
             'state': self.state, **self.kwargs}
        if 'device' in r:
            del r['device']
        return r

    @abstractmethod
    def on_tick(self) -> None:
        """
        Called about each 60 seconds by the communicator thread. This should commence any required
        analyses.

        :attr:`state` is loaded before this call and persisted after it finishes
        """

    def _call_method(self, method: str, *args, **kwargs):
        """
        Securely call a method of this object with provided arguments
        """
        try:
            self.state = self.device.evt_database.get_cache(self.predicate_id)
        except KeyError:
            self.state = None
        try:
            getattr(self, method)(*args, **kwargs)
        finally:
            self.device.evt_database.set_cache(self.predicate_id, self.state)

    def close_event(self, event: Event) -> None:
        """
        Close an event

        :param event: event to close
        """
        if not event.is_closed():
            event.ended_on = time.time()
        self.device.evt_database.close_event(event)

    def open_event(self, msg: str, color: Color) -> tp.Optional[Event]:
        """
        Open an event.

        This automatically checks for current silencing effect, and will return None
        if current time indicates that the event should be silenced.

        :param msg: extra message for the event
        :param color: color of the event
        :return: an Event if silencing is not in effect, else None
        """
        # Check the silencing rules
        localtime = self.device.get_local_time()
        for silencing_period in self.silencing:
            if silencing_period.is_in_time(localtime):
                return

        message = self.verbose_name
        if msg:
            message = '%s: %s' % (message, msg)

        evt = Event(None, None, None, color, False, self.statistic, self.group,
                    message, None, {'predicate_id': self.predicate_id})
        self.device.evt_database.add_event(evt)
        return evt

    def on_group_changed(self, new_group: str) -> None:
        """
        Called upon group changing. This should assign the changed verbose name.

        Called by communicator thread.

        :param new_group: new verbose name
        """
        self.group = new_group

    def on_verbose_name_changed(self, new_verbose_name: str) -> None:
        """
        Called upon verbose name changing. This should assign the changed verbose name.

        Called by communicator thread.

        :param new_verbose_name: new verbose name
        """
        self.verbose_name = new_verbose_name

    def on_configuration_changed(self, new_config: dict) -> None:
        """
        Called upon configuration changing. This should assign the changed configuration.

        Called by communicator thread.

        :param new_config: new configuration
        """
        self.configuration = new_config

    def on_silencing_changed(self, new_silencing: tp.List[DisabledTime]) -> None:
        """
        Called upon silencing rules changing. This should assign the changed silencing.

        Called by communicator thread.

        :param new_silencing: new silencing
        """
        self.silencing = new_silencing

    def on_offline(self) -> None:
        """
        Called when the predicate is disabled or deleted.
        After that, this class will be destroyed, and if the predicate gets enabled again,
        a new instance will be created.

        Called by communicator thread.
        """
