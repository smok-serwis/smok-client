import typing as tp
import weakref
import logging
from abc import ABCMeta, abstractmethod

from satella.coding.structures import OmniHashableMixin


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


class BaseStatistic(metaclass=ABCMeta):
    """
    Base class for your own predicates.

    :ivar device: a weak reference to the SMOKDevice
    :ivar predicate_id: ID of the predicate
    :ivar verbose_name: Human-readable name of this predicate
    :ivar silencing: periods during which the predicate shouldn't generate alerts
    :ivar configuration: a dictionary containing the predicate's configuration
    :cvar statistic_name: name of this statistic
    """

    def __init__(self, device: 'SMOKDevice', predicate_id: str, verbose_name: str, silencing: tp.List[DisabledTime],
                 configuration: tp.Optional[dict], statistic: tp.Optional[str] = None):
        self.device = weakref.proxy(device)
        self.predicate_id = predicate_id
        self.verbose_name = verbose_name
        self.silencing = silencing
        self.configuration = configuration
        self.statistic = statistic

    @property
    @classmethod
    @abstractmethod
    def statistic_name(cls) -> str:     #: obtain the :term:`statistic` name
        ...

    def on_tick(self) -> None:
        """
        Called about each 20 seconds by the communicator thread. This should commence any required
        analyses.
        """

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
