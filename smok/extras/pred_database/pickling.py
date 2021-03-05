import typing as tp
import os
import pickle

from .base import BasePredicateDatabase


class PicklingPredicateDatabase(BasePredicateDatabase):
    def __init__(self, path: str):
        self.__path = path
        self.__predicates = {}
        if os.path.exists(self.__path):
            with open(self.__path, 'rb') as f_in:
                self.__predicates = pickle.load(f_in)

    def __sync(self):
        with open(self.__path, 'wb') as f_out:
            pickle.dump(self.__predicates, f_out, pickle.HIGHEST_PROTOCOL)

    def get_all_predicates(self) -> tp.List[tp.Dict]:
        return list(self.__predicates.values())

    def update_predicate(self, v: tp.Dict) -> None:
        self.__predicates[v['predicate_id']] = v
        self.__sync()

    def set_new_predicates(self, v: tp.List[tp.Dict]):
        self.__predicates = {}
        for dct in v:
            self.__predicates[dct['predicate_id']] = dct
        self.__sync()
