import typing as tp
from abc import ABCMeta, abstractmethod

from smok.sensor import Sensor


class BaseSensorDatabase(metaclass=ABCMeta):
    def __init__(self):
        self.device = None

    def on_register(self, device: 'SMOKDevice') -> None:
        """
        Called by SMOKDevice upon registering this database.

        Called by SMOKDevice's constructor.
        """
        self.device = device

    @abstractmethod
    def get_sensor(self, fqts: str) -> Sensor:
        """
        Return a sensor

        Called by user threads and possibly predicates (so also CommunicatorThread)

        :param fqts: fqts for target sensor, always in canonical form
        :raises KeyError: sensor not defined
        """

    @abstractmethod
    def on_sensors_sync(self, sensors: tp.List[Sensor]):
        """
        Sensors have just been synchronized, this is the entire list.

        Called by communicator threads.
        Will never be called if dont_do_pathpoints is enabled.
        """

    @abstractmethod
    def get_all_sensors(self) -> tp.Iterator[Sensor]:
        """
        Return all sensors stored in the database.

        Called by user threads and possibly predicates (so also CommunicatorThread).
        """
