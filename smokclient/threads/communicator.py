import logging
import typing as tp
import queue

from satella.coding import silence_excs, for_argument
from satella.coding.concurrent import IntervalTerminableThread
from satella.coding.transforms import jsonify

from smokclient.basics import StorageLevel
from smokclient.exceptions import ResponseError
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


class CommunicatorThread(IntervalTerminableThread):
    def __init__(self, device: 'SMOKClient', order_queue: queue.Queue):
        super().__init__(30, name='order getter')
        self.device = device
        self.queue = order_queue

    def fetch_orders(self) -> None:
        resp = self.device.api.post('/v1/device/orders')

        if resp:
            for section in sections_from_list(resp):
                self.queue.put(section)

    def sync_pathpoints(self) -> None:
        pps = self.device.pathpoints.copy_and_clear_dirty()
        data = pathpoints_to_json(pps.values())
        for i in range(3):
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
                break
            except ResponseError as e:
                logger.warning('One failure to sync pathpoints: {e}', exc_info=e)
                continue
        else:
            logger.error('Failed to synchronize pathpoints')
            self.device.pathpoints.update(pps)
            self.device.pathpoints.dirty = True
            return

    def prepare(self):
        # Give the app a moment to prepare and define it's pathpoints
        self.safe_sleep(5)

    @silence_excs(ResponseError)
    def loop(self) -> None:
        # Synchronize the pathpoints
        if self.device.pathpoints.dirty:
            self.sync_pathpoints()

        # Fetch the orders
        self.fetch_orders()
