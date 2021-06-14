import typing as tp
from abc import ABCMeta, abstractmethod


class BasePredicateDatabase(metaclass=ABCMeta):
    """
    One predicate is a dict obtained from it's :meth:`~smok.predicate.BaseStatistic.to_kwargs`.

    All of these methods are called by CommunicatorThread, and
    :meth:`~smok.extras.BasePredicateDatabase.get_all_predicates` by SMOKDevice during
    initialization.
    """

    @abstractmethod
    def get_all_predicates(self) -> tp.List[tp.Dict]:
        """
        Return all predicates
        """

    @abstractmethod
    def update_predicate(self, v: tp.Dict) -> None:
        """
        A single predicate has been changed.

        Note when this is changed there can be no doubt that the predicate has changed. This is
        verified by CommunicatorThread.
        """

    @abstractmethod
    def set_new_predicates(self, v: tp.List[tp.Dict]):
        """
        Called upon a successful predicate synchronization from the server
        """
