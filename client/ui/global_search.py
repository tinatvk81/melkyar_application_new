"""جستجوی سراسری (Ctrl+K) — فایل‌ها + درخواست‌های مشتری، یک‌جا.
نتایج با کیبورد (↑↓/Enter) انتخاب می‌شوند؛ Enter = باز کردن فایل مربوط."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel,
)

from api_client import api_client, ApiError
from ui.property_form import DEAL_TYPE_LABELS, PropertyFormDialog


class GlobalSearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("جستجوی سراسری")
        self.resize(560, 480)
        self._props, self._reqs = [], []

        self.input = QLineEdit()
        self.input.setPlaceholderText("بخشی از آدرس، شهر، نام/تلفن مالک یا مشتری را بنویس…")
        self.input.textChanged.connect(self._search)
        self.results = QListWidget()
        self.results.itemActivated.connect(self._open_item)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Ctrl+K — فایل‌ها و درخواست‌های مشتری همزمان:"))
        lay.addWidget(self.input)
        lay.addWidget(self.results, 1)

    def _search(self, term: str):
        term = (term or "").strip()
        self.results.clear()
        self._props, self._reqs = [], []
        if len(term) < 2:
            return
        # --- فایل‌ها ---
        try:
            resp = api_client.list_properties(search=term, page=1, page_size=20)
            self._props = resp["items"]
        except ApiError:
            self._props = []
        # --- درخواست‌های مشتری (فیلتر سمت کلاینت روی لیست موجود) ---
        try:
            reqs = api_client.list_client_requests()
        except ApiError:
            reqs = []
        t = term.lower()
        self._reqs = [q for q in reqs if
                      t in (q.get("customer_name") or "").lower()
                      or t in (q.get("customer_phone") or "").lower()
                      or t in (q.get("city") or "").lower()
                      or t in (q.get("district") or "").lower()]

        for p in self._props[:10]:
            it = QListWidgetItem(
                f"🏠 #{p['id']} — {p.get('city','')} — {p.get('address') or '—'} — "
                f"{p.get('price_display') or 'توافقی'}")
            it.setData(Qt.UserRole, ("prop", p["id"]))
            self.results.addItem(it)
        for q in self._reqs[:10]:
            st = "باز" if q.get("status") == "open" else "بسته"
            it = QListWidgetItem(
                f"🙋 مشتری: {q['customer_name']} — {DEAL_TYPE_LABELS.get(q.get('deal_type'),'')} — "
                f"{q.get('city') or '—'} — {q.get('customer_phone') or '—'} [{st}]")
            it.setData(Qt.UserRole, ("req", q["id"]))
            self.results.addItem(it)
        if not (self._props or self._reqs):
            self.results.addItem("— چیزی پیدا نشد —")
        if self.results.count():
            self.results.setCurrentRow(0)

    def _open_item(self, item):
        data = item.data(Qt.UserRole)
        if not data:
            return
        kind, _id = data
        if kind == "prop":
            p = next((x for x in self._props if x["id"] == _id), None)
            if p:
                self.close()
                PropertyFormDialog(property_data=p, on_saved=lambda: None).exec()
        # درخواست مشتری: فقط نمایش پیام راهنما — پنجره‌ی درخواست‌ها را خودت باز کن
        elif kind == "req":
            self.close()
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "درخواست مشتری",
                                    "این درخواست در تب «🙋 درخواست مشتری‌ها» است — همان‌جا انتخابش کن.")