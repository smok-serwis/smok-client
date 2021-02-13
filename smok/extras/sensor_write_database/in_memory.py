from satella.coding import Monitor

from .base import BaseSensorWriteDatabase, BaseSensorWriteSynchronization
from ...sensor import SensorWriteEvent


class InMemorySensorWriteDatabase(BaseSensorWriteDatabase, Monitor):
    @Monitor.synchronized
    def on_synced_sw(self, event: SensorWriteEvent):
        self.events.remove(event)

    @Monitor.synchronized
    def on_sync_sw_failed(self, event: SensorWriteEvent):
        pass

    @Monitor.synchronized
    def add_sw(self, event: SensorWriteEvent):
        self.events.add(event)

    @Monitor.synchronized
    def get_sw_sync(self) -> BaseSensorWriteSynchronization:
        return BaseSensorWriteSynchronization(list(self.events), self)

    def __init__(self):
        Monitor.__init__(self)
        self.events = set()
