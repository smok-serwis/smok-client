import logging
import sys
import time
from concurrent.futures import Future

from satella.coding import silence_excs
from satella.coding.concurrent import call_in_separate_thread
from satella.time import time_ms

from smok.basics import Environment, StorageLevel
from smok.client import SMOKDevice
from smok.exceptions import NotReadedError, OperationFailedError
from smok.extras import PicklingArchivesDatabase, PicklingMacroDatabase
from smok.logging import SMOKLogHandler
from smok.pathpoint.orders import AdviseLevel
from smok.pathpoint.pathpoint import Pathpoint
from smok.pathpoint.typing import PathpointValueType
from smok.predicate import BaseStatistic, Color


class PP(Pathpoint):
    """
    A typical memory-backed pathpoint
    """

    def __init__(self, device, name, storage_level=StorageLevel.TREND):
        super().__init__(device, name, storage_level, read_no_often_than=5)
        self.value = 5

    def on_read(self, advise: AdviseLevel) -> int:
        return self.value

    def on_write(self, value: PathpointValueType, advise: AdviseLevel) -> None:
        print(f'Written {self.name} with {value}')
        self.value = value


class CustomPredicate(BaseStatistic):
    """
    A predicate that watches for
    """
    statistic_name = 'test'

    @silence_excs(KeyError, OperationFailedError)
    def on_tick(self) -> None:
        sensor = self.device.get_sensor('value')
        self.device.execute(sensor.read())
        ts, v = sensor.get()
        if v == 10 and self.state is None:
            self.state = self.open_event('Value is equal to 10', Color.RED)
        elif v != 10 and self.state is not None:
            self.close_event(self.state)
            self.state = None


class MyDevice(SMOKDevice):
    def __init__(self):
        super().__init__('dev.crt', 'key.crt', 'predicate_db.pickle',
                         arch_database=PicklingArchivesDatabase('arch_pickle.db'),
                         macro_database=PicklingMacroDatabase('macro_pickle.db'))

    def provide_unknown_pathpoint(self, name: str,
                                  storage_level: StorageLevel = StorageLevel.TREND) -> Pathpoint:
        return PP(self, name, storage_level)

    def sync_sections(self):
        print('Sections synchronized')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARN)
    sd = MyDevice()
    handler = SMOKLogHandler(sd, 'client')
    logging.getLogger().addHandler(handler)
    logging.getLogger().addHandler(logging.StreamHandler(sys.stderr))
    assert sd.device_id == 'skylab'
    assert sd.environment == Environment.STAGING
    print(repr(sd.get_device_info()))
    sd.instrumentation = '{"ok": True}'
    a = PP(sd, 'W2')
    sd.register_statistic(CustomPredicate, lambda stat, cfg: stat == 'my_statistic')
    sd.wait_until_synced()
    n_tn_run = int(sd.metadata.get('n_th.run', '0'))
    n_tn_run += 1
    print('This is the %s-th run' % (n_tn_run, ))
    sd.metadata['n_th.run'] = n_tn_run
    sen = sd.get_sensor('val')
    sd.get_slaves()[0].linkstate = {'status': True}
    assert sd.get_slaves()[0].linkstate == {'status': True}, 'Invalid linkstate!'
    while True:
        with silence_excs(NotReadedError):
            time.sleep(10)
            print(sen.get()[1])
            break
