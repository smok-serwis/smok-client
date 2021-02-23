import os
import pickle
import typing as tp

from satella.coding import Monitor

from smok.extras.sensors_database import BaseSensorDatabase
from smok.sensor import Sensor


def from_dict(device: 'SMOKDevice', data: tuple):
    return Sensor(device, *data)


def to_dict(s: Sensor) -> tuple:
    return s.fqts, s.path, s.type_name


class PicklingSensorDatabase(BaseSensorDatabase, Monitor):
    def __init__(self, path: str):
        super().__init__()
        Monitor.__init__(self)
        self.__path = path
        self.sensor_cache = {}
        if os.path.exists(path):
            try:
                with open(path, 'rb') as f_in:
                    self.__data = pickle.load(f_in)
            except pickle.UnpicklingError:
                self.__data = {}

    @Monitor.synchronized
    def get_sensor(self, fqts: str) -> Sensor:
        if fqts not in self.sensor_cache:
            sensor = from_dict(self.device, self.__data[fqts])
            self.sensor_cache[fqts] = sensor
        return self.sensor_cache[fqts]

    @Monitor.synchronized
    def on_sensors_sync(self, sensors: tp.List[Sensor]):
        self.__data = {}
        for sensor in sensors:
            self.__data[sensor.fqts] = to_dict(sensor)
        self.save()

    def get_all_sensors(self) -> tp.Iterator[Sensor]:
        for key in self.__data.keys():
            yield self.get_sensor(key)

    def save(self):
        with open(self.__path, 'wb') as f_out:
            pickle.dump(self.__data, f_out, pickle.HIGHEST_PROTOCOL)
