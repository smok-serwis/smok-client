import typing as tp

from satella.coding.structures import ReprableMixin, HashableIntEnum
from satella.json import JSONAble


class Environment(HashableIntEnum):
    """
    An environment in which this device runs
    """
    PRODUCTION = 0  #: production
    STAGING = 1  #: testing environment
    LOCAL_DEVELOPMENT = 2  #: CI or local development


class StorageLevel(HashableIntEnum):
    """
    A storage level defines how long is the pathpoint kept at SMOK server.
    """
    PERMANENT = 0  #: hold all values indefinitely
    TREND = 1  #: values at most 2 weeks old will be kept

    def __or__(self, other: 'StorageLevel') -> 'StorageLevel':
        """
        Get the more permissive
        """
        return StorageLevel(self.value | other.value)


class SlaveDeviceInfo(JSONAble, ReprableMixin):
    """
    Information about a slave device attached to primary device

    :ivar device_id: slave device ID (str)
    :ivar master_controller: ID of master device (str)
    :ivar responsible_service: service responsible for this device, mostly "rapid" (str)
    :ivar configuration: a string containing configuration for this device (str)
    """
    _REPR_FIELDS = ('device_id', 'master_controller', 'responsible_service',
                    'configuration')
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

    def to_json(self) -> dict:
        return {
            'device_id': self.device_id,
            'configuration': self.configuration,
            'master_controller': self.master_controller,
            'responsible_service': self.responsible_service
        }


class DeviceInfo(ReprableMixin):
    """
    A class holding device information

    :ivar device_id: device ID of the device (str)
    :ivar slaves: list of :class:`smokclient.basics.SlaveDeviceInfo` containing info
        about the slave devices (tp.List[:class:`~smok.basics.SlaveDeviceInfo`])
    :ivar facets: a set of strings, contains interfaces that access to this device is allowed for
        (tp.Set[str])
    :ivar timezone: local timezone of this device, in accordance with tzdata (str)
    :ivar language: language of this device, according to ISO639-1 (str)
    :ivar units: either `metric` or `imperial`, units used on this device (str)
    :ivar verbose_name: human-readable name of this device (str)
    """
    _REPR_FIELDS = ('device_id', 'facets', 'language', 'timezone', 'units',
                    'slaves')
    __slots__ = ('device_id', 'slaves', 'facets', 'language', 'timezone', 'units',
                 'verbose_name')

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
