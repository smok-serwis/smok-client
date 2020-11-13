import logging
import time
from concurrent.futures import Future

from satella.coding import silence_excs
from satella.coding.concurrent import call_in_separate_thread

from smokclient.basics import Environment, StorageLevel
from smokclient.client import SMOKDevice
from smokclient.exceptions import NotReadedError, OperationFailedError
from smokclient.pathpoint.orders import AdviseLevel
from smokclient.pathpoint.pathpoint import Pathpoint
from smokclient.pathpoint.typing import PathpointValueType
from smokclient.predicate import BaseStatistic, Color


class PP(Pathpoint):
    """
    A typical memory-backed pathpoint
    """

    def __init__(self, device, name, storage_level=StorageLevel.TREND):
        super().__init__(device, name, storage_level)
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
        super().__init__('dev.crt', 'key.crt', 'predicate_db.pickle')

    def provide_unknown_pathpoint(self, name: str,
                                  storage_level: StorageLevel = StorageLevel.TREND) -> Pathpoint:
        return PP(self, name, storage_level)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    sd = MyDevice()
    assert sd.device_id == 'skylab'
    assert sd.environment == Environment.STAGING
    print(repr(sd.get_device_info()))
    sd.instrumentation = '{"ok": True}'
    a = PP(sd, 'W2')
    sd.register_statistic(CustomPredicate)
    sd.wait_until_synced()
    sen = sd.get_sensor('val')
    sd.get_slaves()[0].linkstate = {'status': True}
    assert sd.get_slaves()[0].linkstate == {'status': True}, 'Invalid linkstate!'
    while True:
        with silence_excs(NotReadedError):
            time.sleep(10)
            print(sen.get()[1])
            break
