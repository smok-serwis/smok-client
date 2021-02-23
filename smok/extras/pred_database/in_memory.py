import typing as tp
from smok.extras import BasePredicateDatabase


class InMemoryPredicateDatabase(BasePredicateDatabase):
    def __init__(self):
        self.predicates = []

    def get_all_predicates(self) -> tp.List[tp.Dict]:
        return self.predicates

    def set_new_predicates(self, v: tp.List[tp.Dict]):
        self.predicates = v
