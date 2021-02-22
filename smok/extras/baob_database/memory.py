import typing as tp

from satella.coding import Monitor, silence_excs

from .base import BaseBAOBDatabase


class InMemoryBAOBDatabase(BaseBAOBDatabase, Monitor):
    @Monitor.synchronized
    def set_baob_value(self, key: str, data: bytes, version: int):
        self.baobs_values[key] = data
        self.baobs_versions[key] = version

    @Monitor.synchronized
    def get_all_keys(self) -> tp.Iterator[str]:
        return list(self.baobs_values.keys())

    @Monitor.synchronized
    def get_baob_version(self, key: str) -> int:
        return self.baobs_versions[key]

    @Monitor.synchronized
    @silence_excs(KeyError)
    def delete_baob(self, key: str) -> None:
        del self.baobs_values[key]
        del self.baobs_versions[key]

    @Monitor.synchronized
    def get_baob_value(self, key: str) -> bytes:
        return self.baobs_values[key]

    def __init__(self):
        self.baobs_values = {}
        self.baobs_versions = {}
        Monitor.__init__(self)
