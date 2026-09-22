from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QComboBox, QMessageBox, QHeaderView, QAbstractItemView, QInputDialog,
)
from api_client import api_client, ApiError
from session import handle_api_error
from ui.property_form import DEAL_TYPE_LABELS
from ui.jalali_util import to_jalali_str
class ArchiveTab(QWidget):
    """بایگانی سه‌گانه: غیرفعال / فروخته‌شده / اجاره‌داده‌شده — با چیپ‌های MLK و قیمت."""

    STATUS_TABS = [
        ("inactive", "غیرفعال‌شده‌ها"),
        ("sold", "فروخته‌شده‌ها (معامله قطعی)"),
        ("rented", "اجاره‌داده‌شده‌ها (قرارداد جاری)"),
    ]
    STATUS_COLORS = {"inactive": "#fca5a5", "sold": "#22c55e", "rented": "#7dd3fc"}

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._rows = []

        title_row = QHBoxLayout()
        ttl = QLabel("🗄️ بایگانی فایل‌ها")
        ttl.setStyleSheet("font-size: 15px; font-weight: 800; color: #f5a623; background: transparent;")
        title_row.addWidget(ttl)
        title_row.addSpacing(18)
        self.status_combo = QComboBox()
        for v, l in self.STATUS_TABS:
            self.status_combo.addItem(l, v)
        self.status_combo.currentIndexChanged.connect(self.load_items)
        title_row.addWidget(QLabel("نمایش:"))
        title_row.addWidget(self.status_combo)
        title_row.addStretch()

        bar = QHBoxLayout()
        reactivate_btn = QPushButton("♻️ بازگردانی فایل انتخاب‌شده")
        reactivate_btn.setObjectName("primary")
        reactivate_btn.clicked.connect(self._reactivate)
        bar.addWidget(reactivate_btn)
        if api_client.role == "admin":
            scan_btn = QPushButton("⏳ اسکن فایل‌های قدیمی")
            scan_btn.clicked.connect(self._scan_expiration)
            bar.addWidget(scan_btn)
        bar.addStretch()
        refresh_btn = QPushButton("🔄 به‌روزرسانی")
        refresh_btn.clicked.connect(self.load_items)
        bar.addWidget(refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["#", "شهر", "نوع معامله", "متراژ", "قیمت", "آدرس", "تاریخ ثبت"])
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)

        lay = QVBoxLayout(self)
        lay.addLayout(title_row)
        lay.addSpacing(4)
        lay.addLayout(bar)
        lay.addWidget(self.table)

    def _scan_expiration(self):
        days, ok = QInputDialog.getInt(self, "اسکن فایل‌های قدیمی",
                                       "فایل‌های فعالِ قدیمی‌تر از چند روز بررسی شوند؟", 90, 7, 730)
        if not ok:
            return
        try:
            result = api_client.scan_expiration(days)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        QMessageBox.information(self, "نتیجه",
            f"{result['notified']} فایل کاندید انقضا بود و به مالکش اطلاع‌یه رفت.\n"
            "هر مالک از داخل زنگ اطلاع‌یه تکلیفش را مشخص می‌کند.")

    def load_items(self):
        TableSpinner.show(self.table)
        try:
            resp = api_client.list_archived_properties(
                page=1, page_size=200, status=self.status_combo.currentData())
        except ApiError as e:
            TableSpinner.hide(self.table)
            handle_api_error(self, e, "خطا")
            return
        TableSpinner.hide(self.table)

        self._rows = resp["items"]
        self.table.setRowCount(len(self._rows))
        for r, p in enumerate(self._rows):
            chip = QTableWidgetItem(f"🔖 MLK-{p['id']:04d}")
            chip.setForeground(QColor("#7dd3fc"))
            _cf = chip.font(); _cf.setBold(True); chip.setFont(_cf)
            self.table.setItem(r, 0, chip)
            self.table.setItem(r, 1, QTableWidgetItem(p.get("city") or ""))
            dt_item = QTableWidgetItem(DEAL_TYPE_LABELS.get(p.get("deal_type"), ""))
            _df = dt_item.font(); _df.setBold(True); dt_item.setFont(_df)
            self.table.setItem(r, 2, dt_item)
            _a = p.get("area_m2")
            self.table.setItem(r, 3, QTableWidgetItem(f"{_a:g}" if _a else "—"))
            self.table.setItem(r, 4, QTableWidgetItem(p.get("price_display") or "—"))
            self.table.setItem(r, 5, QTableWidgetItem(p.get("address") or ""))
            self.table.setItem(r, 6, QTableWidgetItem(to_jalali_str(p.get("created_at"))))

    def _reactivate(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "توجه", "ابتدا یک فایل انتخاب کنید.")
            return
        p = self._rows[row]
        if QMessageBox.question(self, "تایید", f"فایل MLK-{p['id']:04d} دوباره فعال شود؟") != QMessageBox.Yes:
            return
        try:
            api_client.reactivate_property(p["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.load_items()