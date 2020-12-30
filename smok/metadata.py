import time
import typing as tp
import queue
from urllib.parse import urlencode, quote_plus

from satella.coding import for_argument, queue_get
from satella.coding.decorators import retry

from smok.exceptions import ResponseError
from smok.extras import BaseMetadataDatabase


class PlainDataUpdater:
    def __init__(self, device: 'SMOKDevice'):
        self.entries = queue.Queue()
        self.device = device

    def add_update(self, key: str, value: str, timestamp: tp.Optional[float] = None):
        timestamp = timestamp or time.time()
        self.entries.put((key, value, timestamp))

    @queue_get('entries', 0)
    @retry(3, exc_classes=ResponseError)
    def try_update(self, msg):
        key, value, timestamp = msg

        if not value:
            self.device.api.delete('/v1/device/metadata/plain/%s' % (urlencode(key), ))
        else:
            self.device.api.put('/v1/device/metadata/plain/%s' % (quote_plus(key), ),
                            json={'value': value, 'unless_timestamp_higher': timestamp})


class StorageDict:
    def __init__(self, device: 'SMOKDevice'):
        self.db = device.meta_database  # type: BaseMetadataDatabase

    def __getitem__(self, item: str) -> str:
        return self.db.get_plain(item)

    @for_argument(None, None, str)
    def __setitem__(self, key: str, value: str):
        self.db.set_plain(key, value)

    def __delitem__(self, key):
        self.db.delete_plain(key)


class PlainMetadata:
    """
    An object representing device's plain metadata.

    Note that this does not support iteration or getting length, but supports
    __setitem__, __delitem__ and __getitem__.
    """
    __slots__ = ('device', 'updater', 'db')

    def try_update(self):
        self.updater.try_update()

    def __init__(self, device: 'SMOKDevice'):
        self.updater = PlainDataUpdater(device)
        self.db = device.meta_database
        self.device = device

    def __getitem__(self, item):
        try:
            return self.db.get_plain(item)
        except KeyError:
            try:
                resp = self.device.api.get('/v1/device/metadata/plain/%s' % (
                    quote_plus(item)
                ))
                value = resp['value']
                self.db.update_plain(item, value, resp['timestamp'])
                return value
            except ResponseError as e:
                if e.status_code == 404:
                    raise KeyError('key not found')
                else:
                    raise

    def get(self, key: str, default=None):
        """
        Get a value for given metadata, returning default if it KeyErrors
        """
        try:
            return self[key]
        except KeyError:
            return default

    @for_argument(None, None, str)
    def __setitem__(self, key, value):
        self.db.put_plain(key, value)
        self.updater.add_update(key, value, time.time())

    def __delitem__(self, key):
        self.db.delete_plain(key)
        self.updater.add_update(key, None, time.time())

