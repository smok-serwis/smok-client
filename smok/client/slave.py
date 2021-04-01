import ujson as ujson
from satella.coding.decorators import retry

from smok.basics import SlaveDeviceInfo
from smok.exceptions import ResponseError


class SlaveDevice:
    """
    A device that's attached to it's master

    :ivar device_id: slave device ID (str)
    :ivar configuration: a string configuring this device (str)
    :ivar responsible_service: should always be "rapid" (str)
    :ivar master_controller: device ID of it's master device (str)
    """
    __slots__ = ('device_id', 'sd', '__linkstate', '__instrumentation',
                 'configuration', 'responsible_service', 'master_controller')

    def __init__(self, sd: 'SMOKDevice', data: SlaveDeviceInfo):
        self.device_id = data.device_id
        self.configuration = data.configuration
        self.responsible_service = data.responsible_service
        self.master_controller = data.master_controller
        self.sd = sd
        self.__linkstate = None
        self.__instrumentation = None

    @property
    def linkstate(self) -> dict:
        """
        An (initially empty) dictionary of format (OpenAPI 3.0):

        .. code-block:: yaml

            type: object
            properties:
                status:
                    type: boolean
                    description: Is the link OK?
                failed_devices:
                    type: array
                    items:
                        type: integer
                        description: Address of the failed device
            required:
                - status

        That tells that status of the device's link, for usage by predicates
        detecting it's failures.

        :returns: current link state
        """
        if self.__linkstate is None:
            resp = self.sd.api.get('/v1/device/instrumentation/%s' % (self.device_id,))
            try:
                linkstate = ujson.loads(resp['linkstate'])
            except ValueError:
                linkstate = {}
            self.__linkstate = linkstate
            self.__instrumentation = resp['instrumentation']
        return self.__linkstate

    @linkstate.setter
    @retry(3, exc_classes=ResponseError)
    def linkstate(self, v: dict) -> None:
        assert 'status' in v, 'Status not in dictionary!'
        self.sd.api.patch('/v1/device/instrumentation/%s' % (self.device_id,), json={
            'linkstate': ujson.dumps(v)
        })
        self.__linkstate = v

    @property
    def instrumentation(self) -> str:
        """
        An arbitrary sequence of characters telling this slave's condition.

        :return: current instrumentation
        """
        if self.__instrumentation is None:
            resp = self.sd.api.get('/v1/device/instrumentation/%s' % (self.device_id,))
            self.__linkstate = resp['linkstate']
            self.__instrumentation = resp['instrumentation']
        return self.__instrumentation

    @instrumentation.setter
    @retry(3, exc_classes=ResponseError)
    def instrumentation(self, v: str) -> None:
        self.sd.api.patch('/v1/device/instrumentation/%s' % (self.device_id,), json={
            'instrumentation': v
        })
        self.__instrumentation = v
