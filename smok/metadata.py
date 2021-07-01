import queue
import time
import typing as tp
from urllib.parse import urlencode, quote_plus

from satella.coding import for_argument, queue_get
from satella.coding.decorators import retry
from satella.coding.structures import CacheDict

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
    def try_update(self, msg) -> None:
        key, value, timestamp = msg

        if not value:
            self.device.api.delete('/v1/device/metadata/plain/%s' % (urlencode(key),))
        else:
            self.device.api.put('/v1/device/metadata/plain/%s' % (quote_plus(key),),
                                json={'value': value, 'unless_timestamp_higher': timestamp})


class StorageDict:
    def __init__(self, device: 'SMOKDevice'):
        self.db = device.meta_database  # type: BaseMetadataDatabase

    def __getitem__(self, item: str) -> str:
        return self.db.get_plain(item)

    @for_argument(None, None, str)
    def __setitem__(self, key: str, value: str) -> None:
        self.db.set_plain(key, value)

    def __delitem__(self, key) -> None:
        self.db.delete_plain(key)


CACHE_MAX_FOR = 60


class PlainMetadata(CacheDict):
    """
    An object representing device's plain metadata.

    Entries will be cached for 60 seconds after downloading them from the server.

    Note that this does not support iteration or getting length, but supports
    __setitem__, __delitem__ and __getitem__.
    """
    __slots__ = ('device', 'updater', 'db', 'cached_for')

    def try_update(self) -> None:
        if self.device.allow_sync:
            self.updater.try_update()

    def __init__(self, device: 'SMOKDevice'):
        self.updater = PlainDataUpdater(device)
        self.db = device.meta_database
        self.device = device
        self.cached_for = {}

    def __getitem__(self, item) -> str:
        try:
            cached_for = self.cached_for[item]
            if time.monotonic() - cached_for > self.device.cache_metadata_for:
                raise KeyError()
            return self.db.get_plain(item)
        except KeyError:
            if not self.device.allow_sync:
                raise
            try:
                resp = self.device.api.get('/v1/device/metadata/plain/%s' % (
                    quote_plus(item)
                ))
                value = resp['value']
                self.db.update_plain(item, value, resp['timestamp'])
                self.cached_for[item] = time.monotonic()
                return value
            except ResponseError as e:
                if e.status_code == 404:
                    raise KeyError('key not found') from e
                return self.db.get_plain(item)

    def get(self, key: str, default=None) -> str:
        """
        Get a value for given metadata, returning default if it KeyErrors
        """
        try:
            return self[key]
        except KeyError:
            return default

    @for_argument(None, None, str)
    def __setitem__(self, key, value) -> None:
        self.db.put_plain(key, value)
        if self.device.allow_sync:
            self.updater.add_update(key, value, time.time())

        self.cached_for[key] = time.monotonic()

    def __delitem__(self, key) -> None:
        self.db.delete_plain(key)
        if self.device.allow_sync:
            self.updater.add_update(key, None, time.time())
        try:
            del self.cached_for[key]
        except KeyError:
            pass
