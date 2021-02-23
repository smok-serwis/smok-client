import typing as tp
import os
import pickle

from .base import BasePredicateDatabase


class PicklingPredicateDatabase(BasePredicateDatabase):
    def __init__(self, path: str):
        self.path = path
        self.predicates = []
        if os.path.exists(self.path):
            with open(self.path, 'rb') as f_in:
                self.predicates = pickle.load(f_in)

    def sync(self):
        with open(self.path, 'wb') as f_out:
            pickle.dump(self.predicates, f_out)

    def get_all_predicates(self) -> tp.List[tp.Dict]:
        return self.predicates

    def set_new_predicates(self, v: tp.List[tp.Dict]):
        self.predicates = v
        self.sync()
