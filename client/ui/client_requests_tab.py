from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QComboBox, QMessageBox, QDialog, QFormLayout, QLineEdit, QTextEdit,
    QHeaderView, QDoubleSpinBox, QAbstractItemView,
)
from PySide6.QtGui import QColor
from api_client import api_client, ApiError
from session import handle_api_error
from ui.spinner import TableSpinner
from ui.property_form import DEAL_TYPE_LABELS, MoneyLineEdit, PersianSpinBox, PersianDoubleSpinBox, PropertyFormDialog
from ui.widgets import AVATAR_COLORS
from ui.widgets import PhoneLineEdit

REQUEST_STATUS_FA = {
    "open": "🆕 جدید", "contacted": "📞 تماس شد", "visited": "🏠 بازدید رفت",
    "negotiation": "🤝 مذاکره", "won": "✅ معامله شد", "lost": "❌ منصرف", "closed": "بسته",
}
REQUEST_STATUS_COLORS = {"open": "#e5e7eb", "contacted": "#7dd3fc", "visited": "#86efac",
                         "negotiation": "#fcd34d", "won": "#22c55e", "lost": "#ef4444", "closed": "#9ca3af"}

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
    """درخواست مشتری‌ها — نوار آمار رنگی + آواتار مشتری + بج وضعیت."""

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._rows = []

        # --- نوار عنوان + چیپ‌های آماری ---
        title_row = QHBoxLayout()
        ttl = QLabel("🙋 درخواست مشتری‌ها")
        ttl.setStyleSheet("font-size: 15px; font-weight: 800; color: #f5a623; background: transparent;")
        title_row.addWidget(ttl)
        title_row.addSpacing(18)
        self._stat_chips = {}
        for key in REQUEST_STATUS_FA:
            chip = QLabel(f"{REQUEST_STATUS_FA[key]}: 0")
            color = REQUEST_STATUS_COLORS.get(key, "#a5b4fc")
            chip.setStyleSheet(
                f"color: {color}; background: rgba(255,255,255,0.05);"
                f"border: 1px solid {color}55; border-radius: 12px;"
                "padding: 4px 12px; font-size: 11px; font-weight: bold;")
            self._stat_chips[key] = chip
            title_row.addWidget(chip)
        title_row.addStretch()

        # --- نوار دکمه‌ها ---
        bar = QHBoxLayout()
        add_btn = QPushButton("➕ درخواست جدید")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(lambda: ClientRequestDialog(on_saved=self.load_requests).exec())
        bar.addWidget(add_btn)
        edit_btn = QPushButton("ویرایش")
        edit_btn.clicked.connect(self._edit)
        bar.addWidget(edit_btn)
        matches_btn = QPushButton("🎯 فایل‌های منطبق")
        matches_btn.clicked.connect(self._matches)
        bar.addWidget(matches_btn)
        self.stage_combo = QComboBox()
        for v, l in REQUEST_STATUS_FA.items():
            self.stage_combo.addItem(l, v)
        stage_btn = QPushButton("ثبت مرحله")
        stage_btn.clicked.connect(self._set_stage)
        bar.addWidget(QLabel("مرحله:"))
        bar.addWidget(self.stage_combo)
        bar.addWidget(stage_btn)
        del_btn = QPushButton("🗑 حذف")
        del_btn.setStyleSheet(
            "QPushButton { color: #f87171; border-color: rgba(239,68,68,0.45); }"
            "QPushButton:hover { background: rgba(239,68,68,0.15); border-color: #ef4444; }")
        del_btn.clicked.connect(self._delete)
        bar.addWidget(del_btn)
        bar.addStretch()
        refresh_btn = QPushButton("🔄 به‌روزرسانی")
        refresh_btn.clicked.connect(self.load_requests)
        bar.addWidget(refresh_btn)

        # --- جدول ---
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["#", "مشتری", "تلفن", "نوع", "شهر/منطقه", "متراژ", "بودجه", "وضعیت"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(lambda _: self._edit())

        lay = QVBoxLayout(self)
        lay.addLayout(title_row)
        lay.addSpacing(4)
        lay.addLayout(bar)
        lay.addWidget(self.table)
        self.load_requests()

    def load_requests(self):
        TableSpinner.show(self.table)
        try:
            self._rows = api_client.list_client_requests()
        except ApiError as e:
            TableSpinner.hide(self.table)
            handle_api_error(self, e, "خطا")
            return
        TableSpinner.hide(self.table)

        # چیپ‌های آماری
        counts = {}
        for q in self._rows:
            st = q.get("status", "open")
            counts[st] = counts.get(st, 0) + 1
        for key, chip in self._stat_chips.items():
            chip.setText(f"{REQUEST_STATUS_FA.get(key, key)}: {counts.get(key, 0)}")

        self.table.setRowCount(len(self._rows))
        for r, q in enumerate(self._rows):
            self.table.setItem(r, 0, QTableWidgetItem(f"#{q['id']}"))

            name = q["customer_name"]
            letter = (name or "?")[:1].upper()
            color = AVATAR_COLORS[(len(name)) % len(AVATAR_COLORS)]
            it = QTableWidgetItem(f"{letter}  {name}")
            it.setForeground(QColor(color))
            _f = it.font(); _f.setBold(True); it.setFont(_f)
            self.table.setItem(r, 1, it)

            self.table.setItem(r, 2, QTableWidgetItem(q.get("customer_phone") or "—"))
            self.table.setItem(r, 3, QTableWidgetItem(DEAL_TYPE_LABELS.get(q.get("deal_type"), q.get("deal_type", ""))))
            city = (q.get("city") or "—") + (f" / {q['district']}" if q.get("district") else "")
            self.table.setItem(r, 4, QTableWidgetItem(city))
            area = f"{q.get('min_area') or '—'} تا {q.get('max_area') or '—'}"
            self.table.setItem(r, 5, QTableWidgetItem(area))
            self.table.setItem(r, 6, QTableWidgetItem(f"{q['max_price']:,}" if q.get("max_price") else "—"))
            st = q.get("status", "open")
            st_item = QTableWidgetItem(f"● {REQUEST_STATUS_FA.get(st, st)}")
            st_item.setForeground(QColor(REQUEST_STATUS_COLORS.get(st, "#eceaf4")))
            _sf = st_item.font(); _sf.setBold(True); st_item.setFont(_sf)
            self.table.setItem(r, 7, st_item)

    # ---------- اکشن‌ها (بدون تغییر) ----------
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

    def _set_stage(self):
        q = self._selected()
        if not q:
            return
        try:
            api_client.update_client_request(q["id"], {"status": self.stage_combo.currentData()})
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