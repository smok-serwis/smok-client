import typing as tp
from abc import ABCMeta, abstractmethod

from smok.pathpoint import PathpointValueType, PathpointType
from smok.pathpoint.typing import to_type

SensorValueType = tp.Union[str, int, float, list, dict]


class BasicType(metaclass=ABCMeta):
    @abstractmethod
    def pathpoint_to_sensor(self, *values: PathpointValueType) -> SensorValueType:
        ...

    @abstractmethod
    def sensor_to_pathpoint(self, value: SensorValueType,
                            *pathpoint_names: str) -> tp.Tuple[PathpointValueType, ...]:
        ...


class NumericType(BasicType):
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
