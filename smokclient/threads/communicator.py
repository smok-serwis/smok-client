import logging
import time
import typing as tp
import queue

from satella.coding import silence_excs, for_argument
from satella.coding.concurrent import TerminableThread
from satella.coding.decorators import retry
from satella.coding.structures import DirtyDict
from satella.coding.transforms import jsonify
from satella.exceptions import WouldWaitMore
from satella.time import measure

from smokclient.basics import StorageLevel
from smokclient.exceptions import ResponseError
from smokclient.pathpoint.data_sync_dict import DataSyncDict
from smokclient.pathpoint.orders import sections_from_list
from smokclient.pathpoint.pathpoint import Pathpoint
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


COMMUNICATOR_INTERVAL = 30


class CommunicatorThread(TerminableThread):
    def __init__(self, device: 'SMOKClient', order_queue: queue.Queue,
                 data_to_sync: DataSyncDict):
        super().__init__(name='order getter')
        self.device = device
        self.queue = order_queue
        self.data_to_sync = data_to_sync
        self.last_sensors_synced = 0

    @retry(3, ResponseError)
    def sync_sensors(self):
        resp = self.device.api.get('/v1/device/sensors')

        sensors = []
        for data in resp:
            sensors.append(Sensor.from_json(data))

        def update_sensors():
            nonlocal sensors

            self.device.sensors = {}
            for sensor in sensors:
                self.device.sensors[sensor.fqts] = sensor

        if not self.last_sensors_synced:
            update_sensors()
            self.device.sensor_lock.release()
            logger.info('Everything is synchronized for %s' % (self.device.device_id, ))
        else:
            with self.device.sensor_lock:
                update_sensors()


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
                if name.startswith('r'):    # Don't use reparse pathpoints
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
            if self.data_to_sync.dirty:
                self.sync_data()

            # Synchronize the pathpoints
            if self.device.pathpoints.dirty:
                self.sync_pathpoints()

            # Fetch the orders
            self.fetch_orders()

            with silence_excs(WouldWaitMore):
                self.data_to_sync.updated_condition.wait(timeout=COMMUNICATOR_INTERVAL-measurement())

            if time.time() - self.last_sensors_synced > SENSORS_SYNC_INTERVAL:
                self.sync_sensors()

