import typing as tp

from .base import BaseStatistic


class StatisticRegistration:
    """
    A proof that given statistic has been registered
    """
    __slots__ = ('matcher', 'stat_class', 'cancelled')

    def __init__(self, matcher: tp.Callable[[str, tp.Dict], bool],
                 stat_class: tp.Type[BaseStatistic]):
        self.matcher = matcher
        self.stat_class = stat_class
        self.cancelled = False

    def cancel(self):
        """
        Cancel this registration.

        Note that this won't update existing predicates.
        """
        self.cancelled = True

    def matches(self, stat_name: str, configuration: tp.Dict):
        if self.cancelled:
            return False
        return self.matcher(stat_name, configuration)


class CollectionOfStatistics:
    __slots__ = ('registrations',)

    def __init__(self):
        self.registrations = []

    def clear(self):
        self.registrations = []

    def clear_cancelled(self):
        self.registrations = [reg for reg in self.registrations if not reg.cancelled]

    def add(self, reg: StatisticRegistration):
        self.registrations.append(reg)

    def try_match(self, *args) -> tp.Optional[tp.Type[BaseStatistic]]:
        if len(args) == 1:
            args = args[0].statistic, args[0].configuration
        self.clear_cancelled()
        reg: StatisticRegistration
        for reg in self.registrations:
            if reg.matches(*args):
                return reg.stat_class
        return None
