import logging
import queue
import time
import typing as tp

from satella.coding import silence_excs, for_argument
from satella.coding.concurrent import TerminableThread
from satella.coding.decorators import retry
from satella.coding.transforms import jsonify
from satella.exceptions import WouldWaitMore
from satella.time import measure

from smokclient.basics import StorageLevel
from smokclient.exceptions import ResponseError
from smokclient.pathpoint.data_sync_dict import DataSyncDict
from smokclient.pathpoint.orders import sections_from_list
from smokclient.pathpoint.pathpoint import Pathpoint
from smokclient.predicate import DisabledTime
from smokclient.predicate.undefined import UndefinedStatistic
from smokclient.sensor import Sensor

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


class CommunicatorThread(TerminableThread):
    def __init__(self, device: 'SMOKClient', order_queue: queue.Queue,
                 data_to_sync: DataSyncDict):
        super().__init__(name='order getter')
        self.device = device
        self.queue = order_queue
        self.data_to_sync = data_to_sync
        self.last_sensors_synced = 0
        self.last_predicates_synced = 0

    def tick_predicates(self):
        for predicate in self.device.predicates.values():
            predicate.on_tick()

    @retry(3, ResponseError)
    def sync_predicates(self):
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
                silencing = [DisabledTime.from_json(dct) for dct in predicate_dict.get('silencing', ())]

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
    def sync_sensors(self):
        resp = self.device.api.get('/v1/device/sensors')

        sensors = []
        for data in resp:
            sensors.append(Sensor.from_json(self.device, data))

        self.device.sensors = {}
        for sensor in sensors:
            self.device.sensors[sensor.fqts] = sensor

        self.last_sensors_synced = time.time()

    @retry(3, ResponseError)
    def fetch_orders(self) -> None:
        resp = self.device.api.post('/v1/device/orders')
        if resp:
            for section in sections_from_list(resp):
                self.queue.put(section)

    @retry(3, ResponseError)
    def sync_data(self) -> None:
        data = self.data_to_sync.to_json()
        try:
            self.device.api.post('/v1/device/pathpoints', json=data)
        except ResponseError as e:
            logger.debug(f'Failed to sync data', exc_info=e)
            self.data_to_sync.add_from_json(data)
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
            logger.debug('Successfully synchronized pathpoints')
        except ResponseError:
            self.device.pathpoints.update(pps)
            self.device.pathpoints.dirty = True
            raise

    def prepare(self):
        # Give the app a moment to prepare and define it's pathpoints
        self.safe_sleep(5)

    def loop(self) -> None:
        with measure() as measurement:
            # Synchronize the data
            if self.data_to_sync.dirty:
                self.sync_data()

            # Synchronize the pathpoints
            if self.device.pathpoints.dirty:
                self.sync_pathpoints()

            # Synchronize sensors
            if time.time() - self.last_sensors_synced > SENSORS_SYNC_INTERVAL:
                self.sync_sensors()

            # Synchronize predicates
            if time.time() - self.last_predicates_synced > PREDICATE_SYNC_INTERVAL:
                self.sync_predicates()

            # Fetch the orders
            self.fetch_orders()

            # Tick the predicates
            self.tick_predicates()

            # Wait for variables to refresh, do we need to upload any?
            with silence_excs(WouldWaitMore):
                if not self.data_to_sync.dirty:
                    timeout = COMMUNICATOR_INTERVAL - measurement()
                    self.data_to_sync.updated_condition.wait(timeout=timeout)
