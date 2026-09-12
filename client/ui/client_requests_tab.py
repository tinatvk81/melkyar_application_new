from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QComboBox, QMessageBox, QDialog, QFormLayout, QLineEdit, QTextEdit,
    QHeaderView, QDoubleSpinBox, QAbstractItemView,
)

from api_client import api_client, ApiError
from session import handle_api_error
from ui.property_form import DEAL_TYPE_LABELS, MoneyLineEdit, PersianSpinBox, PersianDoubleSpinBox, PropertyFormDialog

from ui.widgets import PhoneLineEdit 
class ClientRequestDialog(QDialog):
    def __init__(self, data=None, on_saved=None):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.data = data
        self.on_saved = on_saved
        self.setWindowTitle("ویرایش درخواست مشتری" if data else "درخواست جدید مشتری")
        self.resize(460, 520)

        form = QFormLayout()
        self.name_input = QLineEdit()
        # self.phone_input = QLineEdit()
        self.phone_input = PhoneLineEdit()
        self.type_combo = QComboBox()
        for v, l in DEAL_TYPE_LABELS.items():
            self.type_combo.addItem(l, v)
        self.city_input = QLineEdit()
        self.district_input = QLineEdit()
        self.min_area = PersianDoubleSpinBox()
        self.max_area = PersianDoubleSpinBox()
        self.min_rooms = PersianSpinBox()
        self.max_price = MoneyLineEdit("سقف بودجه (اختیاری)")
        self.notes_input = QTextEdit(); self.notes_input.setFixedHeight(60)
        form.addRow("نام مشتری *:", self.name_input)
        form.addRow("تلفن مشتری:", self.phone_input)
        form.addRow("نوع معامله:", self.type_combo)
        form.addRow("شهر:", self.city_input)
        form.addRow("منطقه/محله:", self.district_input)
        form.addRow("متراژ از:", self.min_area)
        form.addRow("متراژ تا:", self.max_area)
        form.addRow("حداقل اتاق:", self.min_rooms)
        form.addRow("بودجه حداکثر:", self.max_price)
        form.addRow("توضیحات:", self.notes_input)

        if data:
            self.name_input.setText(data.get("customer_name") or "")
            self.phone_input.setText(data.get("customer_phone") or "")
            idx = self.type_combo.findData(data.get("deal_type"))
            self.type_combo.setCurrentIndex(max(idx, 0))
            self.city_input.setText(data.get("city") or "")
            self.district_input.setText(data.get("district") or "")
            self.min_area.setValue(data.get("min_area") or 0)
            self.max_area.setValue(data.get("max_area") or 0)
            self.min_rooms.setValue(data.get("min_rooms") or 0)
            self.max_price.set_value(data.get("max_price"))
            self.notes_input.setPlainText(data.get("notes") or "")

        save_btn = QPushButton("ذخیره"); save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("انصراف"); cancel_btn.clicked.connect(self.reject)
        row = QHBoxLayout(); row.addStretch(); row.addWidget(save_btn); row.addWidget(cancel_btn)

        lay = QVBoxLayout(self); lay.addLayout(form); lay.addLayout(row)

    def _save(self):
        name = self.name_input.text().strip()
        if self.phone_input.text().strip() and not self.phone_input.is_valid():
            QMessageBox.warning(self, "خطا", "شماره تلفن معتبر نیست (فقط رقم، ۱۰ یا ۱۱ رقم).")
            return
        if not name:
            QMessageBox.warning(self, "خطا", "نام مشتری الزامی است.")
            return
        payload = {
            "customer_name": name,
            "customer_phone": self.phone_input.normalized_text() or None,
            "deal_type": self.type_combo.currentData(),
            "city": self.city_input.text().strip() or None,
            "district": self.district_input.text().strip() or None,
            "min_area": self.min_area.value() or None,
            "max_area": self.max_area.value() or None,
            "min_rooms": self.min_rooms.value() or None,
            "max_price": self.max_price.value(),
            "notes": self.notes_input.toPlainText().strip() or None,
            "customer_phone": self.phone_input.normalized_text() or None,
        }
        try:
            if self.data:
                api_client.update_client_request(self.data["id"], payload)
            else:
                api_client.create_client_request(payload)
        except ApiError as e:
            handle_api_error(self, e, "خطا در ذخیره درخواست")
            return
        if self.on_saved:
            self.on_saved()


        self.accept()


class MatchesDialog(QDialog):
    def __init__(self, req):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.req = req
        self.setWindowTitle(f"فایل‌های منطبق — درخواست {req['customer_name']}")
        self.resize(720, 460)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["#", "شهر", "نوع", "متراژ", "آدرس"])
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.doubleClicked.connect(self._open)

        info = QLabel("برای مشاهده/ویرایش فایل، دابل‌کلیک کنید.")
        close_btn = QPushButton("بستن"); close_btn.clicked.connect(self.accept)
        bar = QHBoxLayout(); bar.addWidget(info); bar.addStretch(); bar.addWidget(close_btn)

        lay = QVBoxLayout(self); lay.addLayout(bar); lay.addWidget(self.table)
        self._load()

    def _load(self):
        try:
            rows = api_client.get_request_matches(self.req["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا در تطبیق")
            rows = []
        self._rows = rows
        self.table.setRowCount(len(rows))
        for r, p in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(f"#{p['id']}"))
            self.table.setItem(r, 1, QTableWidgetItem(p.get("city") or ""))
            self.table.setItem(r, 2, QTableWidgetItem(DEAL_TYPE_LABELS.get(p.get("deal_type"), "")))
            self.table.setItem(r, 3, QTableWidgetItem(str(p.get("area_m2") or "")))
            self.table.setItem(r, 4, QTableWidgetItem(p.get("address") or ""))

    def _open(self):
        row = self.table.currentRow()
        if 0 <= row < len(self._rows):
            PropertyFormDialog(property_data=self._rows[row], on_saved=self._load).exec()


class ClientRequestsTab(QWidget):
    """درخواست مشتری‌ها — مشاور فقط درخواست‌های خودش را می‌بیند؛ مدیر همه را."""

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._rows = []

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["#", "مشتری", "تلفن", "نوع", "شهر/منطقه", "متراژ", "بودجه", "وضعیت"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.doubleClicked.connect(lambda _: self._edit())

        add_btn = QPushButton("درخواست جدید")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(lambda: ClientRequestDialog(on_saved=self.load_requests).exec())
        edit_btn = QPushButton("ویرایش")
        edit_btn.clicked.connect(self._edit)
        matches_btn = QPushButton("فایل‌های منطبق")
        matches_btn.clicked.connect(self._matches)
        self.toggle_status_btn = QPushButton("بستن درخواست")
        self.toggle_status_btn.clicked.connect(self._toggle_status)
        del_btn = QPushButton("حذف")
        del_btn.clicked.connect(self._delete)
        refresh_btn = QPushButton("به‌روزرسانی")
        refresh_btn.clicked.connect(self.load_requests)

        bar = QHBoxLayout()
        for b in (add_btn, edit_btn, matches_btn, self.toggle_status_btn, del_btn):
            bar.addWidget(b)
        bar.addStretch()
        bar.addWidget(refresh_btn)

        lay = QVBoxLayout(self)
        lay.addLayout(bar)
        lay.addWidget(self.table)
        self.load_requests()

    def load_requests(self):
        try:
            self._rows = api_client.list_client_requests()
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.table.setRowCount(len(self._rows))
        for r, q in enumerate(self._rows):
            city = (q.get("city") or "—") + (f" / {q['district']}" if q.get("district") else "")
            area = f"{q.get('min_area') or '—'} تا {q.get('max_area') or '—'}"
            self.table.setItem(r, 0, QTableWidgetItem(f"#{q['id']}"))
            self.table.setItem(r, 1, QTableWidgetItem(q["customer_name"]))
            self.table.setItem(r, 2, QTableWidgetItem(q.get("customer_phone") or ""))
            self.table.setItem(r, 3, QTableWidgetItem(DEAL_TYPE_LABELS.get(q.get("deal_type"), q.get("deal_type", ""))))
            self.table.setItem(r, 4, QTableWidgetItem(city))
            self.table.setItem(r, 5, QTableWidgetItem(area))
            self.table.setItem(r, 6, QTableWidgetItem(f"{q['max_price']:,}" if q.get("max_price") else "—"))
            self.table.setItem(r, 7, QTableWidgetItem("باز" if q.get("status") == "open" else "بسته"))

    def _selected(self):
        row = self.table.currentRow()
        if 0 <= row < len(self._rows):
            return self._rows[row]
        QMessageBox.information(self, "توجه", "ابتدا یک درخواست را انتخاب کنید.")
        return None

    def _edit(self):
        q = self._selected()
        if q:
            ClientRequestDialog(data=q, on_saved=self.load_requests).exec()

    def _matches(self):
        q = self._selected()
        if q:
            MatchesDialog(q).exec()

    def _toggle_status(self):
        q = self._selected()
        if not q:
            return
        new_status = "closed" if q["status"] == "open" else "open"
        try:
            api_client.update_client_request(q["id"], {"status": new_status})
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.load_requests()

    def _delete(self):
        q = self._selected()
        if not q:
            return
        if QMessageBox.question(self, "تایید", f"درخواست «{q['customer_name']}» حذف شود؟") != QMessageBox.Yes:
            return
        try:
            api_client.delete_client_request(q["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.load_requests()