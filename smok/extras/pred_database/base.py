import typing as tp
from abc import ABCMeta, abstractmethod


class BasePredicateDatabase(metaclass=ABCMeta):
    """
    One predicate is a dict obtained from it's :meth:`~smok.predicate.BaseStatistic.to_kwargs`
    """
    @abstractmethod
    def get_all_predicates(self) -> tp.List[tp.Dict]:
        """
        Return all predicates
        """

    @abstractmethod
    def set_new_predicates(self, v: tp.List[tp.Dict]):
        """
        Called by CommunicatorThread upon a successful predicate synchronization from the server
        """
