import typing as tp
from abc import ABCMeta, abstractmethod

from smok.sensor import SensorWriteEvent


class BaseSensorWriteSynchronization:
    """
    At most a single instance of this object will be kept alive.

    Must be boolable - return False if this is empty
    """
    __slots__ = ('events', 'swdb')

    def __init__(self, events: tp.List[SensorWriteEvent], swdb: 'BaseSensorWriteDatabase'):
        self.events = events
        self.swdb = swdb

    def __bool__(self):
        return bool(self.events)

    def to_json(self):
        return [event.to_json() for event in self.events]

    def ack(self):
        for event in self.events:
            self.swdb.on_synced_sw(event)

    def nack(self):
        for event in self.events:
            self.swdb.on_sync_sw_failed(event)


class BaseSensorWriteDatabase(metaclass=ABCMeta):
    @abstractmethod
    def on_sync_sw_failed(self, event: SensorWriteEvent):
        """
        Called when given event fails to sync
        """

    @abstractmethod
    def on_synced_sw(self, event: SensorWriteEvent):
        """
        Called when given event becomes synced
        """

    @abstractmethod
    def add_sw(self, event: SensorWriteEvent):
        """
        Add a new event to synchronize
        """

    @abstractmethod
    def get_sw_sync(self) -> BaseSensorWriteSynchronization:
        """
        Get a synchronization
        """
