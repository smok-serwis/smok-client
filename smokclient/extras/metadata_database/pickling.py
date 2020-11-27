import os
import pickle
import time
import typing as tp

from satella.coding import silence_excs

from .base import BaseMetadataDatabase


class PicklingMetadataDatabase(BaseMetadataDatabase):
    """
    Base class for metadata databases that pickles changes to disk after every change.
    """

    @silence_excs(KeyError)
    def delete_plain(self, key: str) -> None:
        del self.db_plain[key]
        self.pickle()

    @silence_excs(KeyError)
    def delete_set(self, key: str) -> None:
        del self.db_set[key]
        self.pickle()

    def pickle(self):
        with open(self.path, 'wb') as f_out:
            pickle.dump((self.db_plain, self.db_set), f_out)

    def __init__(self, path: str):
        self.db_plain = {}
        self.db_set = {}
        self.path = path
        if os.path.exists(self.path):
            try:
                with open(self.path, 'rb') as f_in:
                    self.db_plain, self.db_set = pickle.load(f_in)
            except pickle.PickleError:
                pass

    def put_plain(self, key: str, value: str, timestamp: tp.Optional[float] = None) -> None:
        self.db_plain[key] = value, timestamp or time.time()
        self.pickle()

    def get_plain(self, key: str) -> str:
        return self.db_plain[key][0]

    def update_plain(self, key: str, value: str, timestamp: float) -> None:
        if key not in self.db_plain:
            self.db_plain[key] = value, timestamp
            self.pickle()
        elif self.db_plain[key][1] < timestamp:
            self.db_plain[key] = value, timestamp
            self.pickle()

    def get_all_plain(self) -> tp.Iterator[tp.Tuple[str, str, float]]:
        for key, row in self.db_plain.items():
            yield (key, *row)

    def put_set(self, key: str, value: tp.Set[str], timestamp: tp.Optional[float] = None) -> None:
        self.db_set[key] = value, timestamp or time.time()
        self.pickle()

    def get_set(self, key: str) -> tp.Set[str]:
        return self.db_set[key][0]

    def get_all_set(self) -> tp.Iterator[tp.Tuple[str, tp.Set[str], float]]:
        for key, row in self.db_set.items():
            yield (key, *row)

