import logging
import typing as tp
import weakref

from satella.coding.transforms import merge_series
from satella.coding.typing import Number
from satella.time import time_ms

from smok.exceptions import OperationFailedError
from smok.pathpoint.orders import Section, ReadOrder, AdviseLevel
from smok.sensor.types import SensorValueType, get_type, SVTOrExcept
from .write_logs import SensorWriteEvent

logger = logging.getLogger(__name__)


def fqtsify(tag_name: tp.Union[str, tp.Set[str]]) -> str:
    """
    Standarize the name, for use in dictionaries and other places that access sensors by name

    :param tag_name: :term:`Tag name`, either a space-separated set of names or a set of names
        proper
    :return: :term:`FQTS`-ified name
    """
    if isinstance(tag_name, set):
        tag_name = list(tag_name)
    elif isinstance(tag_name, str):
        tag_name = tag_name.split(' ')
    tag_name.sort()
    return ' '.join(tag_name)


class Sensor:
    """
    A class representing a smok-client sensor defined on given device.

    Class is eq-able and hashable by fqts.

    .. warning:: Do not compare sensors across different devices!

    :ivar fqts: this sensor's :term:`FQTS` (str)
    :ivar path: composite pathpoint names, separated by a tilde (~) (str)
    :ivar type_name: name of the sensor type (str)
    :ivar type: object used for data conversion between pathpoints and sensor values
        (:class:`smok.sensor.types.BasicType`)
    """
    __slots__ = ('fqts', 'path', 'type_name', '_pathpoint_names', 'type', 'device',
                 'slave_pathpoints')

    def __eq__(self, other) -> bool:
        if not isinstance(other, Sensor):
            return False
        return self.fqts == other.fqts

    def __hash__(self) -> int:
        return hash(self.fqts)

    def __init__(self, device: 'SMOKDevice', fqts: str, path: str, type_name: str):
        self.device = weakref.proxy(device)
        self.fqts = fqtsify(fqts)
        self.path = path
        self.type_name = type_name
        self.slave_pathpoints = []
        self._pathpoint_names = []
        for pn in path.split('~'):
            self._pathpoint_names.append(pn)
            self.slave_pathpoints.append(self.device.get_pathpoint(pn))
        self.type = get_type(type_name)

    def get_archive(self,
                    starting_at: int,
                    stopping_at: tp.Optional[int] = None) -> tp.Iterator[
        tp.Tuple[int, SVTOrExcept]]:
        """
        Get archive readings.

        This will be readed entirely from the device's data, the server will not be queried

        :param starting_at: timestamp of start, in milliseconds
        :param stopping_at: timestamp of end, in milliseconds, or None for the end of the park
        :return: an iterator of tuple (timestamp in milliseconds,
                                       pathpoint value or exception instance)
        """
        archives = []
        for slave in self.slave_pathpoints:
            archives.append(slave.get_archive(starting_at, stopping_at))
        merged = merge_series(*archives)
        for ts, *values in merged:
            for v in values:
                if isinstance(v, OperationFailedError):
                    yield ts, v
                    break
            else:
                yield ts, self.type.pathpoint_to_sensor(*values)

    def log_write(self, who: str, reason: str, value: str, hr_value: tp.Optional[str] = None,
                  hr_sensor: tp.Optional[str] = None, timestamp: tp.Optional[int] = None) -> None:
        """
        Log that a write has taken place in this sensor

        :param who: who has made this change
        :param reason: reason for this write
        :param value: a str-able form of value
        :param hr_value: a human-readable value. Defaults to value
        :param hr_sensor: a human-readable name for the sensor. Defaults to fqts
        :param timestamp: in milliseconds! Leave at default for current timestamp
        """
        if hr_value is None:
            hr_value = value
        if hr_sensor is None:
            hr_sensor = self.fqts
        if timestamp is None:
            timestamp = time_ms()
        perm = SensorWriteEvent(fqts=self.fqts, hr_sensor=hr_sensor, hr_value=hr_value, value=value,
                                reason=reason, who=who, timestamp=timestamp)
        self.device.log_sensor_write(perm)

    def write(self, value, advise: AdviseLevel = AdviseLevel.ADVISE) -> Section:
        """
        Write a particular value to the sensor.

        Take care for the value to match the type of the sensor

        :param value: value to write
        :param advise: advise level to use
        :raises TypeError: invalid type
        """
        values = self.type.sensor_to_pathpoint(value)
        section = Section()
        for value, pp in zip(values, self.slave_pathpoints):
            section += pp.write(value, advise)
        return section

    def get(self) -> tp.Tuple[Number, SensorValueType]:
        """
        Return the value of this sensor

        :raises NotReadedError: required pathpoints are not available
        :return: a tuple of (timestamp in milliseconds, sensor value)
        :raises OperationFailedError: one of pathpoint failed to provide a value
        """
        vals = [pp.get() for pp in self.slave_pathpoints]
        cur_ts = max(ts[0] for ts in vals)
        return cur_ts, self.type.pathpoint_to_sensor(*(val[1] for val in vals))

    def read(self, advise: AdviseLevel = AdviseLevel.ADVISE) -> Section:
        return Section([ReadOrder(y, advise) for y in self._pathpoint_names])

    @classmethod
    def from_json(cls, device: 'SMOKDevice', x: dict) -> 'Sensor':
        return Sensor(device, x['fqts'], x['path'], x['type'])
