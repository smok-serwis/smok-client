import typing as tp
import os
import pickle

from .base import BasePredicateDatabase


class PicklingPredicateDatabase(BasePredicateDatabase):
    def __init__(self, path: str):
        self.__path = path
        self.__predicates = []
        if os.path.exists(self.__path):
            with open(self.__path, 'rb') as f_in:
                self.__predicates = pickle.load(f_in)

    def sync(self):
        with open(self.__path, 'wb') as f_out:
            pickle.dump(self.__predicates, f_out)

    def get_all_predicates(self) -> tp.List[tp.Dict]:
        return self.__predicates

    def set_new_predicates(self, v: tp.List[tp.Dict]):
        self.__predicates = v
        self.sync()
