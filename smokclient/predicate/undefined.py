import logging
import typing as tp
from .base import BaseStatistic


logger = logging.getLogger(__name__)


class UndefinedStatistic(BaseStatistic):
    """A placeholder statistic for undefined statistics"""
    statistic_name = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.args = args
        self.kwargs = kwargs

    def initialize(self, cls: tp.Type[BaseStatistic]):
        return cls(*self.args, **self.kwargs)

    def check_device(self):
        for predicate_id in self.device.predicates:
            pred = self.device.predicates[predicate_id]
            if isinstance(pred, UndefinedStatistic):
                statistic_name = pred.statistic
                if statistic_name in self.device.predicate_classes:
                    logger.info(f'Initialized missing predicate ID %s statistic %s' % (
                        predicate_id, statistic_name
                    ))
                    statistic_class = self.device.predicate_classes[statistic_name]
                    self.device.predicates[predicate_id] = pred.initialize(statistic_class)

    def on_tick(self) -> None:
        # check whether the correct statistic classes were loaded and substitute
        # undefined statistic with these
        self.check_device()