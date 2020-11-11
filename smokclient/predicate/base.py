import typing as tp
from abc import ABCMeta, abstractmethod


class Time:
    """
    A representation of a time during a weekday

    :ivar day_of_week: day of week, as per ISO 8601
    :ivar hour: a hour, according to a 24-hour clock
    :ivar minute: a minute
    """
    __slots__ = ('day_of_week', 'hour', 'minute')
    def __init__(self, day_of_week: int, hour: int, minute: int):
        self.day_of_week = day_of_week
        self.hour = hour
        self.minute = minute

    @classmethod
    def from_json(cls, dct: dict) -> 'Time':
        return Time(dct['day'], dct['hour'], dct['minute'])


class DisabledTime:
    """
    Class marking a period during a week

    :ivar start: when this period starts
    :ivar stop: when this period stops
    """
    __slots__ = ('start', 'stop')

    def __init__(self, start: Time, stop: Time):
        self.start = start
        self.stop = stop

    @classmethod
    def from_json(cls, x: dict) -> 'DisabledTime':
        return DisabledTime(Time.from_json(x['start']), Time.from_json(x['stop']))


class BasePredicate(metaclass=ABCMeta):
    """
    Base class for your own predicates.

    :ivar predicate_id: ID of the predicate
    :ivar verbose_name: Human-readable name of this predicate
    :ivar silencing: periods during which the predicate shouldn't generate alerts
    :ivar configuration: a dictionary containing the predicate's configuration
    """

    def __init__(self, predicate_id: str, verbose_name: str, silencing: tp.List[DisabledTime],
                 configuration: dict):
        self.predicate_id = predicate_id
        self.verbose_name = verbose_name
        self.silencing = silencing
        self.configuration = configuration

    @property
    @classmethod
    @abstractmethod
    def statistic_name(cls) -> str:
        """Obtain the :term:`statistic` name"""
