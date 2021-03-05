import typing as tp
from smok.extras import BasePredicateDatabase


class InMemoryPredicateDatabase(BasePredicateDatabase):
    def __init__(self):
        self.predicates = {}

    def get_all_predicates(self) -> tp.List[tp.Dict]:
        return list(self.predicates.values())

    def update_predicate(self, v: tp.Dict) -> None:
        self.predicates[v['predicate_id']] = v

    def set_new_predicates(self, v: tp.List[tp.Dict]):
        self.predicates = {}
        for dct in v:
            self.predicates[dct['predicate_id']] = dct
