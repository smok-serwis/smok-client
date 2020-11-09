import typing as tp
import enum

from satella.json import JSONAble


class Environment(enum.IntEnum):
    """
    An environment in which this device runs
    """
    PRODUCTION = 0              #: production
    STAGING = 1                 #: testing environment
    LOCAL_DEVELOPMENT = 2       #: CI or local development


class StorageLevel(enum.IntEnum):
    """
    A storage level defines how long is the pathpoint kept at SMOK server.
    """
    PERMANENT = 0       #: hold all values indefinitely
    TREND = 1           #: values at most 2 weeks old will be kept


class SlaveDeviceInfo(JSONAble):
    """
    Information about a slave device attached to primary device

    :ivar device_id: slave device ID
    :ivar master_controller: ID of master device
    :ivar responsible_service: service responsible for this device, mostly "rapid"
    :ivar configuration: a string containing configuration for this device
    """
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
        tpl = tuple(map(repr, [self.device_id,
                               self.master_controller,
                               self.responsible_service,
                               self.configuration]))
        return 'SlaveDeviceInfo(%s, %s, %s, %s)' % tpl

    def to_json(self) -> dict:
        return {
            'device_id': self.device_id,
            'configuration': self.configuration,
            'master_controller': self.master_controller,
            'responsible_service': self.responsible_service
        }


class DeviceInfo:
    """
    A class holding device information

    :ivar device_id: device ID of the device
    :ivar slaves: list of :class:`smokclient.basics.SlaveDeviceInfo` containing info
        about the slave devices
    :ivar facets: a set of strings, contains interfaces that access to this device is allowed for
    :ivar timezone: local timezone of this device, in accordance with tzdata
    :ivar language: language of this device, according to ISO639-1
    :ivar units: either `metric` or `imperial`, units used on this device
    :ivar verbose_name: human-readable name of this device
    """
    __slots__ = ('device_id', 'slaves', 'facets', 'language', 'timezone', 'units',
                 'verbose_name')

    def __repr__(self) -> str:
        tpl = tuple(map(repr, [self.device_id, self.facets,
                               self.language, self.timezone,
                               self.units, self.verbose_name,
                               self.slaves]))
        return 'DeviceInfo(%s, %s, %s, %s, %s, %s, %s)' % tpl

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
