import logging
import typing as tp

from satella.coding.transforms import merge_series
from satella.coding.typing import Number
from satella.exceptions import ImpossibleError

from .orders import AdviseLevel, Section
from .typing import PathpointValueType, ValueOrExcept
from .pathpoint import Pathpoint
from ..basics import StorageLevel
from ..exceptions import OperationFailedError
from ..sensor.reparse import parse
from ..sensor.reparse_funs import ecre_eval

logger = logging.getLogger(__name__)


class ReparsePathpoint(Pathpoint):
    """
    A pathpoint whose value is derived from other pathpoints.

    It's first letter is 'r' then there goes the type letter and a Python expression
    with other pathpoints substituted by braces, so eg. rf{W1r4002}+2 would be
    pathpoint "W1r4002" plus two.

    Writing a reparse pathpoint always results in a zero operation, while reading
    it reads all constituent pathpoints.

    Good news is that you don't need to override it, nor provide your own implementations.
    """
    __slots__ = 'expr', 'slave_pathpoints'

    def __init__(self, device: tp.Optional['SMOKDevice'], name: str,
                 storage_level: StorageLevel = StorageLevel.TREND):
        super().__init__(device, name, storage_level)
        self.expr, pps = parse(name[2:])
        self.slave_pathpoints = []
        for pp in pps:
            self.slave_pathpoints.append(device.get_pathpoint(pp, storage_level))

    def on_new_storage_level(self, new_storage_level: StorageLevel) -> None:
        """
        Called when this pathpoint's storage level is updated.

        :param new_storage_level: new storage level for this pathpoint
        """
        for slave in self.slave_pathpoints:
            new_storage_level = slave.storage_level or new_storage_level
            if new_storage_level != slave.storage_level:
                slave.on_new_storage_level(new_storage_level)
        self.storage_level = new_storage_level

    def get_archive(self,
                    starting_at: int,
                    stopping_at: tp.Optional[int] = None) -> tp.Iterator[
        tp.Tuple[int, ValueOrExcept]]:
        """
        Get archive readings.

        This will be readed entirely from the device's data, the server will not be queried

        :param starting_at: timestamp of start, in milliseconds
        :param stopping_at: timestamp of end, in milliseconds, or None for the end of the park
        :return: an iterator of tuple (timestamp in milliseconds,
                                       sensor value or exception instance)
        """
        slave_archives = []
        for slave in self.slave_pathpoints:
            slave_archives.append(slave.get_archive(starting_at, stopping_at))
        merged_series = merge_series(*slave_archives)
        for ts, *values in merged_series:
            for v in values:
                if isinstance(v, OperationFailedError):
                    yield ts, v
                    break
            else:
                yield ts, ecre_eval(self.expr, args=values)

    def set_new_value(self, timestamp: Number, value: ValueOrExcept) -> None:
        """
        A no-op
        """

    def get(self) -> tp.Tuple[Number, PathpointValueType]:
        """
        Calculate the reparse pathpoint's value

        :return: a tuple of (timestamp in milliseconds, value)
        :raises OperationFailedError: when any constituent's pathpoint's read has failed
        """
        timestamps, values = [], []
        for slave in self.slave_pathpoints:
            ts, v = slave.get()
            timestamps.append(ts)
            values.append(v)
        return max(timestamps), ecre_eval(self.expr, args=values)

    def write(self, value, advise_level=AdviseLevel.ADVISE,
              stale_after=None) -> Section:
        """
        Writing a reparse pathpoint is always a zero operation
        """
        return Section()

    def read(self, advise_level=AdviseLevel.ADVISE) -> Section:
        """
        Reading a reparse pathpoint results in all of it's constituents being read.

        :return: a Section, whose execution will result in this pathpoint being re-read
        """
        sec = Section()
        for slave in self.slave_pathpoints:
            sec += slave.read(advise_level)
        return sec

    def on_read(self, advise) -> tp.NoReturn:
        """
        It is an ImpossibleError to call this
        """
        raise ImpossibleError('should never be called!')

    def on_write(self, value, advise) -> tp.NoReturn:
        """
        It is an ImpossibleError to call this
        """
        raise ImpossibleError('should never be called!')
