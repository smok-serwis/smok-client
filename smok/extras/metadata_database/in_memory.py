import time
import typing as tp

from satella.coding import silence_excs

from .base import BaseMetadataDatabase


class InMemoryMetadataDatabase(BaseMetadataDatabase):
    """
    Base class for metadata databases
    """

    @silence_excs(KeyError)
    def delete_plain(self, key: str) -> None:
        del self.db_plain[key]

    @silence_excs(KeyError)
    def delete_set(self, key: str) -> None:
        del self.db_set[key]

    def __init__(self):
        self.db_plain = {}
        self.db_set = {}

    def put_plain(self, key: str, value: str, timestamp: tp.Optional[float] = None) -> None:
        self.db_plain[key] = value, timestamp or time.time()

    def get_plain(self, key: str) -> str:
        return self.db_plain[key][0]

    def update_plain(self, key: str, value: str, timestamp: float) -> None:
        if key not in self.db_plain:
            self.db_plain[key] = value, timestamp
        elif self.db_plain[key][1] < timestamp:
            self.db_plain[key] = value, timestamp

    def get_all_plain(self) -> tp.Iterator[tp.Tuple[str, str, float]]:
        for key, row in self.db_plain.items():
            yield (key, *row)
