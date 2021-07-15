import logging
import base64
import gzip
from logging import LogRecord, Handler

import ujson
from satella.coding.concurrent import SequentialIssuer
from satella.instrumentation import Traceback, frame_from_traceback
from satella.instrumentation.memory import MemoryPressureManager
from satella.time import time_us
from smok.threads.log_publisher import MAX_LOG_BUFFER_SIZE

__all__ = ['SMOKLogHandler']

logger = logging.getLogger(__name__)


class SMOKLogHandler(Handler):
    """
    A logging handler for SMOK

    :param device: SMOKDevice that this logger is attached to
    :param service_name: name of the service
    """

    def __init__(self, device: 'SMOKDevice', service_name: str):
        super().__init__()

        self.service_name = service_name
        self.device = device
        # So timestamps inserted will be monotonically increasing
        self.timestamper = SequentialIssuer(time_us())

        mpm = MemoryPressureManager()
        self.mem_callback = mpm.register_on_entered_severity(2)(self.prune_the_queue)

    def __del__(self):
        self.mem_callback.cancel()

    def prune_the_queue(self):
        while self.device.log_publisher.queue.qsize():
            self.device.log_publisher.queue.get()
        logger.error('Pruned the log queue thanks to low memory condition')

    def record_to_json(self, record: LogRecord):
        ts = self.timestamper.no_less_than(time_us())

        try:
            msg = self.format(record)
        except (TypeError, ValueError):
            try:
                msg = record.message + ' ' + ','.join(map(repr, record.args))
            except AttributeError: # record nas no attribute .message
                try:
                    msg = str(record)
                except TypeError:
                    msg = '<empty>'

        if len(msg) > 1000:
            msg_content = base64.b64encode(
                gzip.compress(msg.encode('utf8'), compresslevel=8)).decode('utf8')
            if len(msg_content) < len(msg):
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
            try:
                tb_json = base64.b64encode(
                    gzip.compress(ujson.dumps(tb.to_json()).encode('utf-8'), 9)).decode('utf-8')
            except OverflowError:
                return None
            dct.update(exception_text=tb.pretty_format(),
                       exception_traceback=tb_json)

        return dct

    def emit(self, record: LogRecord) -> None:
        if self.device.log_publisher.queue.qsize() < MAX_LOG_BUFFER_SIZE:
            le = self.record_to_json(record)
            if le is not None:
                self.device.log_publisher.queue.put(le)

    def close(self) -> None:
        pass
