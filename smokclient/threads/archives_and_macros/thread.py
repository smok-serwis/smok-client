import logging
import time

from satella.coding import silence_excs, ListDeleter
from satella.coding.concurrent import PeekableQueue, IntervalTerminableThread
from satella.coding.decorators import retry
from satella.time import time_as_int

from smokclient.exceptions import ResponseError
from smokclient.pathpoint.orders import Section
from smokclient.threads.archives_and_macros.archive import archiving_entries_from_json, \
    ArchivingEntry
from smokclient.threads.archives_and_macros.macro import macro_parameters_from_json, get_macro, \
    Macro, clean_cache

ARCHIVE_UPDATING_INTERVAL = 600
MACROS_UPDATING_INTERVAL = 600
logger = logging.getLogger(__name__)


class ArchivingAndMacroThread(IntervalTerminableThread):
    def __init__(self, device: 'SMOKDevice', order_queue: PeekableQueue):
        super().__init__(60)
        self.device = device
        self.order_queue = order_queue
        self.archives_updated_on = 0            # type: int
        self.macros_updated_on = 0              # type: int
        self.macros_to_execute = []             # type: tp.List[Macro]
        self.archiving_entries = set()             # type: tp.Set[ArchivingEntry]

    def should_update_archives(self) -> bool:
        return time.time() - self.archives_updated_on > ARCHIVE_UPDATING_INTERVAL

    def should_update_macros(self) -> bool:
        return time.time() - self.macros_updated_on > MACROS_UPDATING_INTERVAL

    @retry(3, exc_classes=ResponseError)
    def update_macros(self) -> None:
        start = self.macros_updated_on
        if start == 0:
            start = time_as_int() - 2*MACROS_UPDATING_INTERVAL
        stop = start + 5 * MACROS_UPDATING_INTERVAL
        resp = self.device.api.get('/v1/device/macro/occurrences/%s-%s' % (
            start, stop
        ))
        macros = [macro_parameters_from_json(macro) for macro in resp]
        self.macros_to_execute = []
        for macro in macros:
            if macro:
                self.macros_to_execute.append(get_macro(*macro))
        self.macros_updated_on = time.time()

    @retry(3, exc_classes=ResponseError)
    def update_archives(self):
        data = self.device.api.get('/v1/device/pathpoints/archived')
        entries_now = archiving_entries_from_json(data)
        entries_to_evict = self.archiving_entries - entries_now
        entries_to_add = entries_now - self.archiving_entries
        for entry in entries_to_evict:
            self.archiving_entries.remove(entry)
        for entry in entries_to_add:
            self.archiving_entries.add(entry)
        self.archives_updated_on = time.time()

    def loop(self) -> None:
        if self.should_update_macros():
            self.update_macros()
            clean_cache()

        if self.should_update_archives():
            self.update_archives()

        with ListDeleter(self.macros_to_execute) as ld:
            for macro in ld:
                if macro.should_execute():
                    macro.execute(self.device, self.order_queue)
                    if not macro:
                        ld.delete()
                        clean_cache()

        sec = Section()
        for a_entry in self.archiving_entries:
            if a_entry.should_update():
                sec += a_entry.update()
        if sec:
            self.order_queue.put(sec)
