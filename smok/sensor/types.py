import typing as tp
from abc import ABCMeta, abstractmethod

from smok.exceptions import OperationFailedError
from smok.pathpoint.typing import to_type, PathpointValueType, PathpointType

SensorValueType = tp.Union[str, int, float, list, dict]
SVTOrExcept = tp.Union[SensorValueType, OperationFailedError]


class BasicType(metaclass=ABCMeta):
    """
    A base class for all SMOK sensor types
    """
    __slots__ = ()

    @abstractmethod
    def pathpoint_to_sensor(self, *values: PathpointValueType) -> SensorValueType:
        """
        Convert a value from pathpoint values to a sensor value
        """

    @abstractmethod
    def sensor_to_pathpoint(self, value: SensorValueType,
                            *pathpoint_names: str) -> tp.Tuple[PathpointValueType, ...]:
        """
        Convert a value from sensor values to pathpoint values, each value in tuple
        for a separate pathpoint. If your sensor consists of a single pathpoint, then
        you should return a 1-element tuple.
        """


class NumericType(BasicType):
    """
    A type for values of numeric type

    :ivar precision: number of places after the comma that should be diplayed (int)
    """
    __slots__ = ('precision', 'multiplier', 'offset')

    def __init__(self, precision=2, multiplier=1, offset=0, **kwargs):
        self.precision = precision
        self.multiplier = multiplier
        self.offset = offset

    def pathpoint_to_sensor(self, *values: PathpointValueType):
        value = values[0]
        value = value * self.multiplier + self.offset
        return round(value, self.precision)

    def sensor_to_pathpoint(self, value: SensorValueType,
                            *pathpoint_names: str) -> tp.Tuple[PathpointValueType, ...]:
        value = (value - self.offset) / self.multiplier
        return to_type(value, PathpointType.get_type(pathpoint_names[0])),


class UnicodeType(BasicType):
    """
    A basic type for Unicode-containing sensors
    """

    def sensor_to_pathpoint(self, value: SensorValueType,
                            *pathpoint_names: str) -> tp.Tuple[PathpointValueType, ...]:
        return str(value),

    def pathpoint_to_sensor(self, *values: PathpointValueType) -> SensorValueType:
        return str(values[0])


CACHE_DICT = {}  # type: tp.Dict[str, NumericType]


def get_type(type_name: str) -> NumericType:
    global CACHE_DICT

    if type_name not in CACHE_DICT:
        if type_name == 'std.Number10':
            type_ = NumericType(multiplier=0.1)
        elif type_name == 'std.Unicode':
            type_ = UnicodeType()
        elif type_name == 'frisko.DayOfWeek':
            type_ = NumericType(offset=-1)
        elif type_name == 'std.Number100':
            type_ = NumericType(multiplier=0.01)
        elif '(' in type_name:
            arguments = type_name.split('(', 1)[1]
            arguments = arguments.rsplit(')', 1)[0]
            type_ = eval('NumericType(%s)' % (arguments,), {'NumericType': NumericType})
        else:
            type_ = NumericType()
        CACHE_DICT[type_name] = type_

    return CACHE_DICT[type_name]
