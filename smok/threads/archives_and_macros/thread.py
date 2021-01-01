import logging
import time

from satella.coding import silence_excs
from satella.coding.concurrent import PeekableQueue, IntervalTerminableThread
from satella.coding.decorators import retry
from satella.time import time_as_int

from smok.exceptions import ResponseError
from smok.pathpoint.orders import Section
from smok.threads.archives_and_macros.archive import archiving_entries_from_json, \
    ArchivingEntry, archiving_dict_from_json
from smok.macro import Macro

ARCHIVE_UPDATING_INTERVAL = 600
MACROS_UPDATING_INTERVAL = 600
logger = logging.getLogger(__name__)


class ArchivingAndMacroThread(IntervalTerminableThread):
    def __init__(self, device: 'SMOKDevice', order_queue: PeekableQueue, dont_do_macros,
                 dont_do_archives):
        super().__init__(60)
        self.dont_do_macros = dont_do_macros
        self.dont_do_archives = dont_do_archives
        self.device = device
        self.order_queue = order_queue
        self.archives_updated_on = 0  # type: int
        self.macros_updated_on = 0  # type: int
        self.macros_to_execute = []  # type: tp.List[Macro]
        self.archiving_entries = set()  # type: tp.Set[ArchivingEntry]

        # Load the archiving data
        for interval, pathpoints in self.device.arch_database.get_archiving_instructions().items():
            for pp in pathpoints:
                self.archiving_entries.add(ArchivingEntry(pp, interval))

    def should_update_archives(self) -> bool:
        return time.time() - self.archives_updated_on > ARCHIVE_UPDATING_INTERVAL

    def should_update_macros(self) -> bool:
        return time.time() - self.macros_updated_on > MACROS_UPDATING_INTERVAL

    @retry(3, exc_classes=ResponseError)
    def update_macros(self) -> None:
        start = self.macros_updated_on
        if start == 0:
            start = time_as_int() - 2 * MACROS_UPDATING_INTERVAL
        stop = start + 5 * MACROS_UPDATING_INTERVAL
        resp = self.device.api.get('/v1/device/macro/occurrences/%s-%s' % (
            start, stop
        ))
        macros = [Macro.from_json(self.device, macro) for macro in resp]
        macros_to_execute = [macro for macro in macros if macro]
        self.device.macros_database.set_macros(macros_to_execute)
        self.macros_updated_on = time.time()

    @retry(3, exc_classes=ResponseError)
    def update_archives(self):
        data = self.device.api.get('/v1/device/pathpoints/archived')
        entries_now = archiving_entries_from_json(data)
        dct = archiving_dict_from_json(data)
        self.device.arch_database.on_archiving_data_sync(dct)
        entries_to_evict = self.archiving_entries - entries_now
        entries_to_add = entries_now - self.archiving_entries
        for entry in entries_to_evict:
            self.archiving_entries.remove(entry)
        for entry in entries_to_add:
            self.archiving_entries.add(entry)
        self.archives_updated_on = time.time()

    def loop(self) -> None:
        if not self.dont_do_macros:
            if self.should_update_macros():
                self.update_macros()

            mdb = self.device.macros_database

            for macro in mdb.get_macros():
                if macro.should_execute():
                    macro.execute()

            for macro_id, ts in mdb.get_done_macros():
                logger.warning(f'Syncing {macro_id} {ts}')
                with silence_excs(ResponseError):
                    self.device.api.post('/v1/device/macros/%s/%s' % (macro_id, ts))
                    mdb.notify_macro_synced(macro_id, ts)

        self.device.metadata.try_update()

        if not self.dont_do_archives:
            if self.should_update_archives():
                self.update_archives()

            sec = Section()
            for a_entry in self.archiving_entries:
                if a_entry.should_update():
                    sec += a_entry.update()
            if sec:
                self.order_queue.put(sec)
