import typing as tp
from abc import ABCMeta, abstractmethod

from smok.sensor import Sensor


class BaseSensorDatabase(metaclass=ABCMeta):
    def __init__(self):
        self.device = None

    def on_register(self, device: 'SMOKDevice') -> None:
        """
        Called by SMOKDevice upon registering this database
        """
        self.device = device

    @abstractmethod
    def get_sensor(self, fqts: str) -> Sensor:
        """
        Return a sensor

        :param fqts: fqts for target sensor, always in canonical form
        :raises KeyError: sensor not defined
        """

    @abstractmethod
    def on_sync(self, sensors: tp.List[Sensor]):
        """
        Sensors have just been synchronized, this is the entire list
        """

    @abstractmethod
    def get_all_sensors(self) -> tp.Iterator[Sensor]:
        """
        Return all sensors stored in the database
        """
