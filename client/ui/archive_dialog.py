from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QMessageBox
)

from api_client import api_client, ApiError
from session import handle_api_error
from ui.property_form import DEAL_TYPE_LABELS


class ArchivePropertiesDialog(QDialog):
    """
    فهرست فایل‌های غیرفعال‌شده (آرشیو) + دکمه‌ی بازگردانی. قبل از این دیالوگ،
    فایل غیرفعال‌شده عملاً برای همیشه از دسترس خارج می‌شد چون هیچ راهی برای
    دیدن یا برگرداندنش نبود.
    """

    def __init__(self, on_restored):
        super().__init__()
        self.on_restored = on_restored
        self._properties_by_row = []
        self._current_page = 1
        self._total_pages = 1

        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("آرشیو فایل‌های غیرفعال‌شده")
        self.resize(700, 500)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["شهر", "نوع معامله", "آدرس", "متراژ"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        restore_btn = QPushButton("بازگردانی فایل انتخاب‌شده")
        restore_btn.clicked.connect(self.handle_restore_selected)

        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.accept)

        top_bar = QHBoxLayout()
        top_bar.addWidget(restore_btn)
        top_bar.addStretch()
        top_bar.addWidget(close_btn)

        self.prev_btn = QPushButton("◀ صفحه‌ی قبل")
        self.prev_btn.clicked.connect(self.handle_prev_page)
        self.next_btn = QPushButton("صفحه‌ی بعد ▶")
        self.next_btn.clicked.connect(self.handle_next_page)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)

        pagination_bar = QHBoxLayout()
        pagination_bar.addWidget(self.prev_btn)
        pagination_bar.addStretch()
        pagination_bar.addWidget(self.status_label)
        pagination_bar.addStretch()
        pagination_bar.addWidget(self.next_btn)

        layout = QVBoxLayout()
        layout.addLayout(top_bar)
        layout.addWidget(self.table)
        layout.addLayout(pagination_bar)
        self.setLayout(layout)

        self.load_archived()

    def load_archived(self):
        try:
            response = api_client.list_archived_properties(page=self._current_page)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return

        properties = response["items"]
        self._total_pages = response["total_pages"]
        self._properties_by_row = properties

        self.table.setRowCount(len(properties))
        for row, p in enumerate(properties):
            self.table.setItem(row, 0, QTableWidgetItem(p.get("city", "")))
            self.table.setItem(row, 1, QTableWidgetItem(DEAL_TYPE_LABELS.get(p.get("deal_type"), p.get("deal_type", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(p.get("address") or ""))
            self.table.setItem(row, 3, QTableWidgetItem(str(p.get("area_m2") or "")))

        self.status_label.setText(
            f"صفحه {self._current_page} از {self._total_pages} — تعداد کل: {response['total']}"
        )
        self.prev_btn.setEnabled(self._current_page > 1)
        self.next_btn.setEnabled(self._current_page < self._total_pages)

    def handle_prev_page(self):
        if self._current_page > 1:
            self._current_page -= 1
            self.load_archived()

    def handle_next_page(self):
        if self._current_page < self._total_pages:
            self._current_page += 1
            self.load_archived()

    def handle_restore_selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._properties_by_row):
            QMessageBox.information(self, "توجه", "ابتدا یک فایل را از فهرست انتخاب کنید.")
            return
        prop = self._properties_by_row[row]

        confirm = QMessageBox.question(
            self, "تایید", f"فایل «{prop.get('address') or prop.get('city')}» به فهرست فعال برگردانده شود؟"
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            api_client.reactivate_property(prop["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return

        QMessageBox.information(self, "موفق", "فایل با موفقیت بازگردانده شد.")
        self.load_archived()
        self.on_restored()
