import logging
from concurrent.futures import Future

from satella.coding.concurrent import call_in_separate_thread

from smokclient.basics import Environment
from smokclient.client import SMOKDevice
from smokclient.pathpoint.orders import AdviseLevel
from smokclient.pathpoint.pathpoint import Pathpoint
from smokclient.pathpoint.typing import PathpointValueType


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    sd = SMOKDevice('dev.crt', 'key.crt')
    assert sd.device_id == 'skylab'
    assert sd.environment == Environment.STAGING
    print(repr(sd.get_device_info()))

    class PP(Pathpoint):
        def __init__(self, name):
            super().__init__(name)
            self.value = 5

        @call_in_separate_thread()
        def on_read(self, advise: AdviseLevel) -> Future:
            print(f'Readed {self.name}')
            return self.value

        @call_in_separate_thread()
        def on_write(self, value: PathpointValueType, advise: AdviseLevel) -> Future:
            print(f'Written {self.name} with {value}')
            self.value = value

    a = PP('W1')
    sd.register_pathpoint(a)
