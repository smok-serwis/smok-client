import base64
import gzip
from logging import LogRecord, Handler

import ujson
from satella.coding import Monitor
from satella.coding.concurrent import SequentialIssuer
from satella.instrumentation import Traceback, frame_from_traceback
from satella.time import time_us

__all__ = ['SMOKLogHandler']


class SMOKLogHandler(Handler, Monitor):
    """
    A logging handler for SMOK

    :param device: SMOKDevice that this logger is attached to
    :param service_name: name of the service
    """

    def __init__(self, device: 'SMOKDevice', service_name: str):
        super().__init__()
        Monitor.__init__(self)

        self.service_name = service_name
        self.device = device
        # So timestamps inserted will be monotonically increasing
        self.timestamper = SequentialIssuer(time_us())

    def record_to_json(self, record: LogRecord):
        ts = self.timestamper.no_less_than(time_us())

        # noinspection PyBroadException
        try:
            msg = self.format(record)
        except (TypeError, ValueError):
            msg = record.message + ' ' + ','.join(map(repr, record.args))

        if len(msg) > 1000:
            msg_content = base64.b64encode(
                gzip.compress(msg.encode('utf8'), compresslevel=8)).decode('utf8')
            msg = {'encoding': 'base64-gzip', 'content': msg_content}

        dct = {
            'service': self.service_name,
            'when': ts,
            'message': msg,
            'level': record.levelno,
        }

        if record.exc_info:
            f = frame_from_traceback(record.exc_info[2])
            tb = Traceback(f)
            tb_json = base64.b64encode(
                gzip.compress(ujson.dumps(tb.to_json()).encode('utf-8'), 9)).decode('utf-8')
            dct.update(exception_text=tb.pretty_format(),
                       exception_traceback=tb_json)

        return dct

    def emit(self, record: LogRecord) -> None:
        self.device.log_publisher.queue.put(self.record_to_json(record))

    def close(self) -> None:
        pass
