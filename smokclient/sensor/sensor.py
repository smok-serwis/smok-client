import typing as tp
import weakref

from satella.coding import rethrow_as
from satella.coding.typing import Number

from smokclient.exceptions import NotReadedError
from smokclient.pathpoint import AdviseLevel, PathpointValueType
from smokclient.pathpoint.orders import Section
from smokclient.sensor.reparse import reparse_to_native_components, parse
from smokclient.sensor import reparse_funs
from smokclient.sensor.types import NumericType, SensorValueType, get_type


def fqtsify(tag_name: tp.Union[str, tp.Set[str]]) -> str:
    """
    Standarize the name, for use in dictionaries and other places that access sensors by name

    :param tag_name: either a space-separated set of names or a set of names proper
    :return: FQTS-ified name
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

    :ivar fqts: a sorted string representing tags of this sensor joined by a space
    :ivar path: composite pathpoint names, separated by a tilde (~)
    :ivar type_name: name of the sensor type
    :ivar type: object used for data conversion between pathpoints and sensor values
    """
    __slots__ = ('fqts', 'path', 'type_name', '_pathpoint_names', 'type', 'device')

    def __init__(self, device: 'SMOKDevice', fqts: str, path: str, type_name: str):
        self.device = weakref.proxy(device)
        self.fqts = fqtsify(fqts)
        self.path = path
        self._pathpoint_names = path.split('~')
        self.type_name = type_name
        self.type = get_type(type_name)

    @rethrow_as(KeyError, NotReadedError)
    def _calculate_pathpoint(self, path: str) -> tp.Tuple[Number, PathpointValueType]:
        if path[0] == 'r':
            exp, pathpoints = parse(path)
            exp = exp[2:]   # skip reparse declaration and reparse point type
            pathpoint_vals = [self._calculate_pathpoint(pp) for pp in pathpoints]
            dct, ts = {}, None
            for i, pp_val in enumerate(pathpoint_vals):
                if ts is None:
                    ts = pp_val[0]
                elif pp_val[0] < ts:
                    ts = pp_val[0]
                dct['v%s' % (i, )] = pp_val[1]
            return ts, eval(exp, reparse_funs.__dict__, dct)
        else:
            pp = self.device.get_pathpoint(path)     # throws KeyError
            return pp.get()

    def get(self) -> tp.Tuple[Number, SensorValueType]:
        """
        Return the value of this sensor

        :raises NotYetReaded: required pathpoints are not available
        :return: a tuple of (timestamp, sensor value)
        :raises OperationFailedError: one of pathpoint failed to provide a value
        """
        vals = [self._calculate_pathpoint(pp) for pp in self._pathpoint_names]
        cur_ts = max(ts[0] for ts in vals)
        return cur_ts, self.type.pathpoint_to_sensor(*(val[1] for val in vals))

    def read(self, advise: AdviseLevel = AdviseLevel.ADVISE) -> Section:
        pass

    @classmethod
    def from_json(cls, device: 'SMOKDevice', x: dict) -> 'Sensor':
        return Sensor(device, x['fqts'], x['path'], x['type'])
