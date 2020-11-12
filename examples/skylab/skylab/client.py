import logging
import time
from concurrent.futures import Future

from satella.coding import silence_excs
from satella.coding.concurrent import call_in_separate_thread

from smokclient.basics import Environment, StorageLevel
from smokclient.client import SMOKDevice
from smokclient.exceptions import NotReadedError
from smokclient.pathpoint.orders import AdviseLevel
from smokclient.pathpoint.pathpoint import Pathpoint
from smokclient.pathpoint.typing import PathpointValueType
from smokclient.predicate import BaseStatistic


class PP(Pathpoint):
    def __init__(self, name, storage_level = StorageLevel.TREND):
        super().__init__(name, storage_level)
        self.value = 5

    @call_in_separate_thread()
    def on_read(self, advise: AdviseLevel) -> Future:
        print(f'Readed {self.name}')
        return self.value

    @call_in_separate_thread()
    def on_write(self, value: PathpointValueType, advise: AdviseLevel) -> Future:
        print(f'Written {self.name} with {value}')
        self.value = value


class CustomPredicate(BaseStatistic):
    statistic_name = 'test'

    def on_tick(self) -> None:
        print('Ticked!')


class MyDevice(SMOKDevice):
    def __init__(self):
        super().__init__('dev.crt', 'key.crt')

    def provide_unknown_pathpoint(self, name: str,
                                  storage_level: StorageLevel = StorageLevel.TREND) -> Pathpoint:
        print(f'Tried to provide for {name} with sl={storage_level}')
        raise KeyError()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    sd = MyDevice()
    assert sd.device_id == 'skylab'
    assert sd.environment == Environment.STAGING
    print(repr(sd.get_device_info()))
    sd.instrumentation = '{"ok": True}'
    a = PP(sd, 'W1')
    sd.register_statistic(CustomPredicate)
    sd.wait_until_synced()
    sen = sd.get_sensor('val')
    while True:
        with silence_excs(NotReadedError):
            time.sleep(10)
            print(sen.get()[1])
            break
    print('Value obtained')
