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

from smok.extras import BasePathpointDatabase
from smok.pathpoint.orders import sections_from_list
from smok.pathpoint.pathpoint import Pathpoint
from smok.predicate import DisabledTime
from smok.predicate.undefined import UndefinedStatistic
from smok.sensor import Sensor
from smok.sync_workers.base import SyncError

logger = logging.getLogger(__name__)

SENSORS_SYNC_INTERVAL = 300


@for_argument(returns=jsonify)
def pathpoints_to_json(pps: tp.Iterable[Pathpoint]) -> list:
    output = []
    for pp in pps:
        output.append({'path': pp.name,
                       'storage_level': pp.storage_level})
    return output


COMMUNICATOR_INTERVAL = 60
PREDICATE_SYNC_INTERVAL = 300
BAOB_SYNC_INTERVAL = 60 * 60  # an hour


def redo_data(data):
    """
    Alter the data received from the backend to our way
    """
    output = []
    for pp in data:
        values = []
        for ts in pp['values']:
            if isinstance(ts, dict):
                if 'error_code' in ts:
                    values.append([False, ts['timestamp'], ts['error_code']])
                else:
                    values.append([ts['timestamp'], ts['value']])
            else:
                values.append(ts)
        output.append({'path': pp['path'],
                       'values': values})
    return output


class CommunicatorThread(TerminableThread):
    def __init__(self, device: 'SMOKClient', order_queue: queue.Queue,
                 data_to_sync: BasePathpointDatabase, dont_obtain_orders: bool,
                 dont_do_baobs: bool, dont_do_pathpoints: bool,
                 dont_do_predicates: bool,
                 dont_sync_sensor_writes: bool,
                 startup_delay: float):
        super().__init__(name='order getter')
        self.dont_sync_sensor_writes = dont_sync_sensor_writes
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
            kwargs = predicate.to_kwargs()
            # noinspection PyProtectedMember
            predicate._call_method('on_tick')
            new_kwargs = predicate.to_kwargs()
            if kwargs != new_kwargs:
                self.device.pred_database.update_predicate(new_kwargs)

    @retry(3, ResponseError)
    def sync_events(self) -> None:
        evt_to_sync = self.device.evt_database.get_events_to_sync()
        if evt_to_sync is None:
            return
        try:
            json = [evt.to_json() for evt in evt_to_sync.get_events()]
            resp = self.device.api.post('/v1/device/alarms',
                                        json=json)
            evt_to_sync.acknowledge(*(data['uuid'] for data in resp))
            self.device.on_successful_sync()
        except ResponseError as e:
            if e.is_no_link():
                self.device.on_failed_sync()
            logger.error('Failure syncing events: %s', e, exc_info=e)
            evt_to_sync.negative_acknowledge()
            raise

    @retry(3, ResponseError)
    def sync_predicates(self) -> None:
        try:
            resp = self.device.api.get('/v1/device/predicates')
        except ResponseError as e:
            if e.is_no_link():
                self.device.on_failed_sync()
            raise

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
                    cfg = predicate_dict['configuration']
                    base_class = self.device.statistic_registration.try_match(stat_name, cfg)
                    if base_class is None:
                        base_class = UndefinedStatistic
                    predicate = base_class(self.device, predicate_id,
                                           predicate_dict['verbose_name'],
                                           silencing, cfg, stat_name)
                    self.device.predicates[predicate_id] = predicate
                else:
                    stat = self.device.predicates[predicate_id]
                    config = predicate_dict['configuration']
                    verbose_name = predicate_dict['verbose_name']
                    group = predicate_dict['group']
                    if stat.configuration != config:
                        stat.on_configuration_changed(config)
                    if stat.silencing != silencing:
                        stat.on_silencing_changed(silencing)
                    if stat.verbose_name != verbose_name:
                        stat.on_verbose_name_changed(verbose_name)
                    if stat.group != group:
                        stat.on_group_changed(group)

                predicate_dict['silencing'] = silencing

        predicates_to_delete = set(self.device.predicates.keys()) - predicates_found
        for predicate_id in predicates_to_delete:
            self.device.predicates[predicate_id].on_offline()
            del self.device.predicates[predicate_id]

        if not self.last_predicates_synced:
            self.device.ready_lock.release()
        self.last_predicates_synced = time.monotonic()
        self.db_sync_predicates()
        self.device.on_successful_sync()

    def db_sync_predicates(self):
        lst = [predicate.to_kwargs() for predicate in self.device.predicates.values()]
        self.device.pred_database.set_new_predicates(lst)

    @retry(3, ResponseError)
    def sync_sensors(self) -> None:
        try:
            resp = self.device.api.get('/v1/device/sensors')

            self.device.sensor_database.on_sensors_sync(
                [Sensor.from_json(self.device, data) for data in resp])
            self.last_sensors_synced = time.monotonic()
            self.device.on_successful_sync()
        except ResponseError as e:
            if e.is_no_link():
                self.device.on_failed_sync()
            raise

    @retry(3, ResponseError)
    def fetch_orders(self) -> None:
        try:
            resp = self.device.api.post('/v1/device/orders')
            if resp:
                for section in sections_from_list(resp):
                    self.queue.put(section)
            self.device.on_successful_sync()
        except ResponseError as e:
            if e.is_no_link():
                self.device.on_failed_sync()
            raise

    @retry(3, ResponseError)
    def sync_sensor_writes(self) -> None:
        sync = self.device.sensor_write_database.get_sw_sync()
        if not sync:
            return
        try:
            self.device.api.put('/v1/device/sensor/write_log', json=sync.to_json())
            sync.ack()
            self.device.on_successful_sync()
        except ResponseError as e:
            if e.is_no_link():
                self.device.on_failed_sync()
            if not e.is_clients_fault():
                logger.warning('Failed to sync sensor writes: %s', e, exc_info=e)
                sync.nack()
                raise
            else:
                logger.warning('Got HTTP %s on sync sensor writes, acking', e.status_code)
                sync.ack()

    @retry(3, SyncError)
    def sync_data(self) -> None:
        sync = self.data_to_sync.get_data_to_sync()
        if sync is None:
            return
        try:
            data = sync.to_json()
            if not data:
                sync.acknowledge()
                return
            self.device.sync_worker.sync_pathpoints(redo_data(data))
            sync.acknowledge()
            self.device.on_successful_sync()
        except SyncError as e:
            if e.is_no_link():
                self.device.on_failed_sync()
            if not e.is_clients_fault():
                sync.negative_acknowledge()
            else:
                logger.warning('Got HTTP %s while syncing pathpoint data. '
                               'Assuming is it damaged and marking as synced', e.status_code)
                sync.acknowledge()

    def sync_baob(self) -> None:
        self._sync_baob()
        self.device.baobs_loaded = True

    @retry(3, ResponseError)
    def _sync_baob(self) -> None:
        try:
            keys = self.device.baob_database.get_all_keys()
            data = []
            for key in keys:
                try:
                    data.append({'key': key,
                                 'version': self.device.baob_database.get_baob_version(key)})
                except KeyError:
                    logger.error('Got key %s but the DB tells us that it does not exist', key)
                    continue
            data = self.device.api.post('/v1/device/baobs', json=data)

            for key_to_delete in data['should_delete']:
                self.device.baob_database.delete_baob(key_to_delete)

            for key_to_download in data['should_download']:
                resp, headers = self.device.api.get(f'/v1/device/baobs/{key_to_download}',
                                                    direct_response=True)
                self.device.baob_database.set_baob_value(key_to_download, resp,
                                                         int(headers['X-SMOK-BAOB-Version']))
                if self.last_baob_synced:
                    self.device.on_baob_updated(key_to_download)

            for key_to_upload in data['should_upload']:
                self.device.api.put(f'/v1/device/baobs/{key_to_upload}', files={
                    'file': self.device.baob_database.get_baob_value(key_to_upload),
                    'data': ujson.dumps(
                        {'version': self.device.baob_database.get_baob_version(
                            key_to_upload)}).encode(
                        'utf8')
                })
            self.last_baob_synced = time.monotonic()
            self.device.on_successful_sync()
        except ResponseError as e:
            if e.is_no_link():
                self.device.on_failed_sync()
            raise

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
            self.device.on_successful_sync()
        except ResponseError as e:
            if e.is_no_link():
                self.device.on_failed_sync()
            self.device.pathpoints.update(pps)
            self.device.pathpoints.dirty = True
            raise

    def prepare(self) -> None:
        # Give the app a moment to prepare and define it's pathpoints
        self.safe_sleep(self.startup_delay)

    def wait(self, time_taken: float):
        time_to_wait = COMMUNICATOR_INTERVAL - time_taken
        while time_to_wait > 0.1 and not self.terminating:  # for float roundings
            try:
                ttw = min(time_to_wait, 5)
                self.data_to_update.wait(timeout=ttw)
                return
            except WouldWaitMore:
                time_to_wait -= ttw

    @log_exceptions(logger, logging.ERROR)
    def loop(self) -> None:
        with measure() as measurement:
            # Synchronize the data
            monotime = time.monotonic()

            if self.device.allow_sync:
                logger.debug('Sync allowed, making a pass')
                if not self.dont_do_pathpoints:
                    self.sync_data()

                    # Synchronize the pathpoints
                    if self.device.pathpoints.dirty:
                        self.sync_pathpoints()

                    # Synchronize sensors
                    if monotime - self.last_sensors_synced > SENSORS_SYNC_INTERVAL:
                        self.sync_sensors()

                # Synchronize predicates
                if not self.dont_do_predicates:
                    if monotime - self.last_predicates_synced > PREDICATE_SYNC_INTERVAL:
                        self.sync_predicates()

                # Fetch the BAOBs
                if not self.dont_do_baobs:
                    if monotime - self.last_baob_synced > BAOB_SYNC_INTERVAL:
                        self.sync_baob()
                if not self.dont_sync_sensor_writes:
                    self.sync_sensor_writes()

                # Fetch the orders
                if not self.dont_obtain_orders and not self.device.sync_worker.has_async_orders:
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
            else:
                logger.debug('Sync was disallowed')

            # Wait for variables to refresh, do we need to upload any?
            self.wait(measurement())
