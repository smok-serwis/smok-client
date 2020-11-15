import base64
import gzip
from logging import LogRecord, Handler

from satella.coding import Monitor
from satella.coding.transforms import stringify
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
        self.last_timestamp_in_us = None

    def record_to_json(self, record: LogRecord):
        jsonified_extra = {}
        if record.args:
            jsonified_extra.update(args=stringify(record.args))

        ts = time_us()
        with Monitor.acquire(self):
            if self.last_timestamp_in_us is not None:
                if ts <= self.last_timestamp_in_us:
                    ts = self.last_timestamp_in_us + 1
            self.last_timestamp_in_us = ts

        dct = {
            'service': self.service_name,
            'when': ts,
            'message': f'[{record.name},{record.thread}] [{record.pathname}:{record.lineno}:] {record.msg}',
            'level': record.levelno,
        }
        if jsonified_extra:
            dct['extra'] = jsonified_extra

        if record.exc_info:
            f = frame_from_traceback(record.exc_info[2])
            tb = Traceback(f)
            tb_json = base64.b64encode(gzip.compress(tb.to_json().encode('utf-8'), 9)).decode('utf-8')
            dct.update(exception_text=tb.pretty_format(),
                       exception_traceback=tb_json)

        return dct

    def emit(self, record: LogRecord) -> None:
        self.device.log_publisher.queue.put(self.record_to_json(record))

    def close(self) -> None:
        pass

