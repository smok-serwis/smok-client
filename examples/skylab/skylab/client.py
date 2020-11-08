import logging
from concurrent.futures._base import Future

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

        def on_read(self, advise: AdviseLevel) -> Future:
            @call_in_separate_thread()
            def read(advised: AdviseLevel):
                print(f'Readed {self.name}')
                return self.value
            return read(advise)

        def on_write(self, value: PathpointValueType, advise: AdviseLevel) -> Future:
            @call_in_separate_thread()
            def write(val, advised: AdviseLevel):
                print(f'Written {self.name} with {val}')
                self.value = val
            return write()

    a = PP('W1')
    sd.register_pathpoint(a)
