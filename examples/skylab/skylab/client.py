from smokclient.basics import Environment
from smokclient.client import SMOKDevice

if __name__ == '__main__':
    sd = SMOKDevice('dev.crt', 'key.crt')
    assert sd.device_id == 'skylab'
    assert sd.environment == Environment.STAGING
    print(repr(sd.get_device_info()))
