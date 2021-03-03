import os
import pickle

from .in_memory import InMemorySensorWriteDatabase
from smok.sensor import SensorWriteEvent


class PicklingSensorWriteDatabase(InMemorySensorWriteDatabase):
    def __init__(self, pickle_addr: str):
        super().__init__()
        self.__path = pickle_addr
        if os.path.exists(pickle_addr):
            try:
                with open(pickle_addr, 'rb') as f_in:
                    self.events = pickle.load(f_in)
            except IOError:
                self.events = set()
        else:
            self.events = set()

    def sync(self):
        with open(self.__path, 'wb') as f_out:
            pickle.dump(self.events, f_out, pickle.HIGHEST_PROTOCOL)

    def add_sw(self, event: SensorWriteEvent):
        super().add_sw(event)
        self.sync()

    def on_synced_sw(self, event: SensorWriteEvent):
        super().on_synced_sw(event)
        self.sync()
