import logging
import queue
import time
import typing as tp

import ujson
from satella.coding import silence_excs, for_argument, log_exceptions
from satella.coding.concurrent import TerminableThread, Condition
from satella.coding.decorators import retry
from satella.coding.transforms import jsonify
from satella.exceptions import WouldWaitMore
from satella.time import measure

from smok.basics import StorageLevel
from smok.exceptions import ResponseError
from smok.extras.event_database import BaseEventSynchronization
from smok.pathpoint.data_sync_dict import DataSyncDict
from smok.pathpoint.orders import sections_from_list
from smok.pathpoint.pathpoint import Pathpoint
from smok.predicate import DisabledTime
from smok.predicate.undefined import UndefinedStatistic
from smok.sensor import Sensor

logger = logging.getLogger(__name__)

SENSORS_SYNC_INTERVAL = 300


@for_argument(returns=jsonify)
def pathpoints_to_json(pps: tp.Iterable[Pathpoint]) -> list:
    output = []
    for pp in pps:
        output.append({'path': pp.name,
                       'storage_level': pp.storage_level})
    return output


COMMUNICATOR_INTERVAL = 20
PREDICATE_SYNC_INTERVAL = 300
BAOB_SYNC_INTERVAL = 60*60  # an hour


class CommunicatorThread(TerminableThread):
    def __init__(self, device: 'SMOKClient', order_queue: queue.Queue,
                 data_to_sync: DataSyncDict, dont_obtain_orders: bool,
                 dont_do_baobs: bool, dont_do_pathpoints: bool,
                 dont_do_predicates: bool,
                 startup_delay: float):
        super().__init__(name='order getter')
        self.device = device
        self.startup_delay = startup_delay
        self.dont_do_pathpoints = dont_do_pathpoints
        self.dont_do_baobs = dont_do_baobs
        self.dont_obtain_orders = dont_obtain_orders
        self.queue = order_queue
        self.dont_do_predicates = dont_do_predicates
        self.data_to_sync = data_to_sync
        self.last_sensors_synced = 0
        self.last_predicates_synced = 0
        self.data_to_update = Condition()
        self.last_baob_synced = 0

    def tick_predicates(self) -> None:
        for predicate in self.device.predicates.values():
            # noinspection PyProtectedMember
            predicate._call_method('on_tick')

    @retry(3, ResponseError)
    def sync_events(self) -> None:
        evt_to_sync = self.device.evt_database.get_events_to_sync()  # type: BaseEventSynchronization
        if evt_to_sync is None:
            return
        try:
            resp = self.device.api.post('/v1/device/alarms',
                                        json=[evt.to_json() for evt in evt_to_sync.get_events()])
            evt_to_sync.acknowledge(*(data['uuid'] for data in resp))
        except ResponseError as e:
            logger.error('Failure syncing events', exc_info=e)
            evt_to_sync.negative_acknowledge()
            raise

    @retry(3, ResponseError)
    def sync_predicates(self) -> None:
        resp = self.device.api.get('/v1/device/predicates')

        predicates_found = set()
        for predicate_dict in resp:
            predicate_id = predicate_dict['predicate_id']
            predicates_found.add(predicate_id)
            if not predicate_dict['online']:
                if predicate_id in self.device.predicates:
                    self.device.predicates[predicate_id].on_offline()
                    del self.device.predicates[predicate_id]
            else:
                silencing = [DisabledTime.from_json(dct) for dct in
                             predicate_dict.get('silencing', ())]

                if predicate_id not in self.device.predicates:
                    stat_name = predicate_dict['statistic']
                    stat_class = self.device.predicate_classes.get(stat_name, UndefinedStatistic)
                    predicate = stat_class(self.device, predicate_id,
                                           predicate_dict['verbose_name'], silencing,
                                           predicate_dict['configuration'],
                                           predicate_dict['statistic'])
                    self.device.predicates[predicate_id] = predicate
                else:
                    stat = self.device.predicates[predicate_id]
                    config = predicate_dict['configuration']
                    if stat.configuration != config:
                        stat.on_configuration_changed(config)
                    if stat.silencing != silencing:
                        stat.on_silencing_changed(silencing)

            predicates_to_delete = set(self.device.predicates.keys()) - predicates_found
            for predicate_id in predicates_to_delete:
                self.device.predicates[predicate_id].on_offline()
                del self.device.predicates[predicate_id]

        if not self.last_predicates_synced:
            self.device.ready_lock.release()
        self.last_predicates_synced = time.time()

    @retry(3, ResponseError)
    def sync_sensors(self) -> None:
        resp = self.device.api.get('/v1/device/sensors')

        self.device.sensor_database.on_sensors_sync([Sensor.from_json(self.device, data) for data in resp])
        self.last_sensors_synced = time.time()

    @retry(3, ResponseError)
    def fetch_orders(self) -> None:
        resp = self.device.api.post('/v1/device/orders')
        if resp:
            for section in sections_from_list(resp):
                self.queue.put(section)

    @retry(3, ResponseError)
    def sync_sensor_writes(self) -> None:
        sync = self.device.sensor_write_database.get_sync()
        if not sync:
            return
        try:
            self.device.api.put('/v1/device/sensor/write_log', json=sync.to_json())
            sync.ack()
        except ResponseError:
            sync.nack()

    @retry(3, ResponseError)
    @log_exceptions(logger, logging.WARNING, 'Failed to sync data: {e}')
    def sync_data(self) -> None:
        sync = self.data_to_sync.get_data_to_sync()
        if sync is None:
            return
        try:
            data = sync.to_json()
            if not data:
                sync.acknowledge()
                return
            self.device.api.post('/v1/device/pathpoints', json=data)
            sync.acknowledge()
        except ResponseError as e:
            if e.status_code // 100 == 5:
                logger.debug(f'Failed to sync data', exc_info=e)
                sync.negative_acknowledge()
                raise
            else:
                logger.warning(str(data))
                logger.warning(f'Got HTTP {e.status_code} while syncing pathpoint data. '
                               f'Assuming is it damaged and marking as synced')
                sync.acknowledge()

    def sync_baob(self):
        self._sync_baob()
        self.device.baobs_loaded = True

    @retry(3, ResponseError)
    def _sync_baob(self) -> None:
        keys = self.device.baob_database.get_all_keys()
        data = []
        for key in keys:
            data.append({'key': key,
                         'version': self.device.baob_database.get_baob_version(key)})
        data = self.device.api.post('/v1/device/baobs', json=data)
        for key_to_download in data['should_download']:
            resp, headers = self.device.api.get(f'/v1/device/baobs/{key_to_download}',
                                                direct_response=True)
            self.device.baob_database.set_baob_value(key_to_download, resp, int(headers['X-SMOK-BAOB-Version']))
            logger.debug('Downloaded BAOB %s', key_to_download)
        for key_to_upload in data['should_upload']:
            self.device.api.put(f'/v1/device/baobs/{key_to_upload}', files={
                'file': self.device.baob_database.get_baob_value(key_to_upload),
                'data': ujson.dumps({'version': self.device.baob_database.get_baob_version(key_to_upload)}).encode('utf8')
            })
            logger.debug('Uploaded BAOB %s', key_to_upload)
        self.last_baob_synced = time.time()

    @retry(3, ResponseError)
    def sync_pathpoints(self) -> None:
        pps = self.device.pathpoints.copy_and_clear_dirty()
        data = pathpoints_to_json(pps.values())
        try:
            resp = self.device.api.put('/v1/device/pathpoints', json=data)
            for pp in resp:
                name = pp['path']
                if name.startswith('r'):  # Don't use reparse pathpoints
                    continue
                with silence_excs(KeyError):
                    pathpoint = self.device.provide_unknown_pathpoint(name, StorageLevel(
                        pp.get(
                            'storage_level',
                            1)))
                    stor_level = StorageLevel(pp.get('storage_level', 1))
                    if stor_level != pathpoint.storage_level:
                        pathpoint.on_new_storage_level(stor_level)
        except ResponseError:
            self.device.pathpoints.update(pps)
            self.device.pathpoints.dirty = True
            raise

    def prepare(self) -> None:
        # Give the app a moment to prepare and define it's pathpoints
        self.safe_sleep(self.startup_delay)

    def loop(self) -> None:
        with measure() as measurement:
            # Synchronize the data
            if not self.dont_do_pathpoints:
                self.sync_data()

                # Synchronize the pathpoints
                if self.device.pathpoints.dirty:
                    self.sync_pathpoints()

                # Synchronize sensors
                if time.time() - self.last_sensors_synced > SENSORS_SYNC_INTERVAL:
                    self.sync_sensors()

            # Synchronize predicates
            if not self.dont_do_predicates:
                if time.time() - self.last_predicates_synced > PREDICATE_SYNC_INTERVAL:
                    self.sync_predicates()

            # Fetch the BAOBs
            if not self.dont_do_baobs:
                if time.time() - self.last_baob_synced > BAOB_SYNC_INTERVAL:
                    self.sync_baob()

            self.sync_sensor_writes()

            # Fetch the orders
            if not self.dont_obtain_orders:
                self.fetch_orders()

            if not self.dont_do_predicates:
                # Tick the predicates
                self.tick_predicates()

                # Sync the events
                self.sync_events()

            # Checkpoint the DB
            if not self.dont_do_pathpoints:
                self.device.pp_database.checkpoint()
            if not self.dont_do_predicates:
                self.device.evt_database.checkpoint()

            # Wait for variables to refresh, do we need to upload any?
            time_to_wait = COMMUNICATOR_INTERVAL - measurement()
            while time_to_wait > 0.1:       # for float roundings
                try:
                    ttw = min(time_to_wait, 5)
                    self.data_to_update.wait(timeout=ttw)
                    break
                except WouldWaitMore:
                    time_to_wait -= ttw * 1.1
