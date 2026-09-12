from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QComboBox, QMessageBox, QHeaderView, QAbstractItemView,
)
from PySide6.QtWidgets import QInputDialog
from api_client import api_client, ApiError
from session import handle_api_error
from ui.property_form import DEAL_TYPE_LABELS


class ArchiveTab(QWidget):
    """بایگانی: فایل‌های غیرفعال‌شده + فایل‌های معامله‌شده (sold)."""

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._rows = []

        self.status_combo = QComboBox()
        self.status_combo.addItem("غیرفعال‌شده‌ها", "inactive")
        self.status_combo.addItem("فروخته‌شده‌ها (معامله قطعی)", "sold")
        self.status_combo.currentIndexChanged.connect(self.load_items)

        reactivate_btn = QPushButton("بازگردانی فایل انتخاب‌شده")
        reactivate_btn.setObjectName("primary")
        reactivate_btn.clicked.connect(self._reactivate)
        refresh_btn = QPushButton("به‌روزرسانی")
        refresh_btn.clicked.connect(self.load_items)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("نمایش:"))
        bar.addWidget(self.status_combo)
        # bar.addWidget(reactivate_btn)
        # self.load_items()


        bar.addWidget(reactivate_btn)
        if api_client.role == "admin":
            scan_btn = QPushButton("⏳ اسکن فایل‌های قدیمی")
            scan_btn.clicked.connect(self._scan_expiration)
            bar.addWidget(scan_btn)
        bar.addStretch()


        # bar.addStretch()
        bar.addWidget(refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["#", "شهر", "نوع معامله", "متراژ", "آدرس", "تاریخ ثبت"])
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        lay = QVBoxLayout(self)
        lay.addLayout(bar)
        lay.addWidget(self.table)


        # if api_client.role == "admin":
        #     scan_btn = QPushButton("⏳ اسکن فایل‌های قدیمی")
        #     scan_btn.clicked.connect(self._scan_expiration)
        #     bar.addWidget(scan_btn)

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
        try:
            resp = api_client.list_archived_properties(
                page=1, page_size=200, status=self.status_combo.currentData()
            )
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self._rows = resp["items"]
        self.table.setRowCount(len(self._rows))
        for r, p in enumerate(self._rows):
            self.table.setItem(r, 0, QTableWidgetItem(str(p["id"])))
            self.table.setItem(r, 1, QTableWidgetItem(p.get("city") or ""))
            self.table.setItem(r, 2, QTableWidgetItem(DEAL_TYPE_LABELS.get(p.get("deal_type"), "")))
            self.table.setItem(r, 3, QTableWidgetItem(str(p.get("area_m2") or "")))
            self.table.setItem(r, 4, QTableWidgetItem(p.get("address") or ""))
            self.table.setItem(r, 5, QTableWidgetItem((p.get("created_at") or "")[:10]))

    def _reactivate(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "توجه", "ابتدا یک فایل انتخاب کنید.")
            return
        p = self._rows[row]
        if QMessageBox.question(self, "تایید", f"فایل #{p['id']} دوباره فعال شود؟") != QMessageBox.Yes:
            return
        try:
            api_client.reactivate_property(p["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.load_items()