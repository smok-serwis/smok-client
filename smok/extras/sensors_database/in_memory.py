import typing as tp

from satella.coding import Monitor

from .base import BaseSensorDatabase
from ...sensor import Sensor


class InMemorySensorDatabase(BaseSensorDatabase, Monitor):
    @Monitor.synchronized
    def get_all_sensors(self) -> tp.Iterator[Sensor]:
        return list(self.sensors.values())

    @Monitor.synchronized
    def on_sensors_sync(self, sensors: tp.List[Sensor]):
        self.sensors = {sensor.fqts: sensor for sensor in sensors}

    @Monitor.synchronized
    def get_sensor(self, fqts: str) -> Sensor:
        return self.sensors[fqts]

    def __init__(self):
        super().__init__()
        Monitor.__init__(self)
        self.sensors = {}  # type: tp.Dict[str, Sensor]
