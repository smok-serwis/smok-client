import enum
import typing as tp

from satella.coding.transforms import clip

from smok.exceptions import OperationFailedError

PathpointValueType = tp.Union[int, float, str]

ValueOrExcept = tp.Union[PathpointValueType, OperationFailedError]


class PathpointType(enum.Enum):
    B = 'B'  #: binary, 0 or 1
    W = 'W'  #: unsigned 16-bit
    w = 'w'  #: signed 16-bit
    f = 'f'  #: IEEE 754 float
    d = 'd'  #: IEEE 754 double
    u = 'u'  #: an Unicode string

    @staticmethod
    def get_type(path: str) -> 'PathpointType':
        """
        Return the type of given pathpoint

        :return: type of the pathpoint
        """
        if path[0] == 'r':
            return PathpointType(path[1])
        else:
            return PathpointType(path[0])


def to_type(value: PathpointValueType, type_: PathpointType) -> PathpointValueType:
    """
    Coerces a value to target pathpoint type

    :param value: value to coerce
    :param type_: type of target pathpoint
    :return: a coerced value
    """
    if type_ == PathpointType.B:
        v = bool(int(value))
    elif type_ == PathpointType.W:
        v = clip(int(value), 0, 65535)
    elif type_ == PathpointType.w:
        v = clip(int(value), -32768, 32767)
    elif type_ in (PathpointType.f, PathpointType.d):
        v = float(value)
    elif type_ == PathpointType.u:
        v = str(value)
    else:
        raise ValueError('Invalid type given')
    return v
