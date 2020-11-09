import logging
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

logger = logging.getLogger(__name__)


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
                with silence_excs(KeyError):
                    if name not in pps:
                        new_pp = self.device.unknown_pathpoint_provider(name,
                                                                        StorageLevel(
                                                                            pp.get(
                                                                                'storage_level',
                                                                                1)))
                        self.device.pathpoints[name] = new_pp
                        self.device.pathpoints.clear_dirty()
                    pathpoint = pps[name]
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
