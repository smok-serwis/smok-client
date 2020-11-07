import typing as tp
import enum

from satella.json import JSONAble


class Environment(enum.IntEnum):
    PRODUCTION = 0
    STAGING = 1
    LOCAL_DEVELOPMENT = 2


class SlaveDeviceInfo(JSONAble):
    __slots__ = ('device_id', 'master_controller', 'responsible_service',
                 'configuration')

    def __init__(self, device_id: str, master_controller: str, responsible_service: str,
                 configuration: str):
        self.device_id = device_id
        self.master_controller = master_controller
        self.responsible_service = responsible_service
        self.configuration = configuration

    @classmethod
    def from_json(cls, dct: dict) -> 'SlaveDeviceInfo':
        return SlaveDeviceInfo(dct['device_id'], dct['master_controller'],
                               dct['responsible_service'], dct['configuration'])

    def __repr__(self) -> str:
        return 'SlaveDeviceInfo(%s, %s, %s, %s)' % map(repr, [self.device_id,
                                                              self.master_controller,
                                                              self.responsible_service,
                                                              self.configuration])

    def to_json(self) -> dict:
        return {
            'device_id': self.device_id,
            'configuration': self.configuration,
            'master_controller': self.master_controller,
            'responsible_service': self.responsible_service
        }


class DeviceInfo:
    __slots__ = ('device_id', 'slaves', 'facets', 'language', 'timezone', 'units',
                 'verbose_name')

    def __repr__(self) -> str:
        return 'DeviceInfo(%s, %s, %s, %s, %s, %s, %s)' % map(repr, [self.device_id, self.facets,
                                                                     self.language, self.timezone,
                                                                     self.units, self.verbose_name,
                                                                     self.slaves])

    def __init__(self, device_id: str, facets: tp.Set[str], language: str, timezone: str,
                 units: str, verbose_name: str, slaves: tp.List[SlaveDeviceInfo]):
        self.device_id = device_id
        self.facets = facets
        self.language = language
        self.timezone = timezone
        self.units = units
        self.verbose_name = verbose_name
        self.slaves = slaves

    @classmethod
    def from_json(cls, dct: dict) -> 'DeviceInfo':
        ccon = dct['culture_context']
        return DeviceInfo(dct['device_id'], set(dct['facets']), ccon['language'],
                          ccon['timezone'], ccon['units'], dct['verbose_name'],
                          [SlaveDeviceInfo.from_json(y) for y in dct['slave_devices']])
