from collections import OrderedDict
from threading import Lock

from config import settings
from schemas.schemas import StoredReport


class ReportStore:
    """Armazenamento em memória thread-safe para relatórios processados.

    Suficiente para um MVP/demonstração. Em produção, troque por Redis ou
    um banco de dados persistente mantendo a mesma interface.
    """

    def __init__(self, max_items: int) -> None:
        self._items: "OrderedDict[str, StoredReport]" = OrderedDict()
        self._lock = Lock()
        self._max_items = max_items

    def save(self, report: StoredReport) -> None:
        with self._lock:
            self._items[report.report_id] = report
            self._items.move_to_end(report.report_id)
            while len(self._items) > self._max_items:
                self._items.popitem(last=False)

    def get(self, report_id: str) -> StoredReport | None:
        with self._lock:
            return self._items.get(report_id)

    def update(self, report: StoredReport) -> None:
        self.save(report)


report_store = ReportStore(max_items=settings.report_ttl_items)
