from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QAbstractItemView
)

from api_client import api_client, ApiError
from session import handle_api_error
from ui.spinner import TableSpinner
from ui.toast import Toast


class DiscoveryTab(QWidget):
    """یافته‌های ملک‌یاب — آگهی‌های کشف‌شده از دیوار/شیپور که هنوز به فایل تبدیل نشدن."""

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._listings = []

        title = QLabel("📡 یافته‌های ملک‌یاب")
        title.setStyleSheet("font-size: 15px; font-weight: 800; color: #f5a623; background: transparent;")

        refresh_btn = QPushButton("🔄 به‌روزرسانی")
        refresh_btn.clicked.connect(self.refresh)

        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch()
        header.addWidget(refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["عنوان", "محله", "قیمت", "منبع", "تاریخ", ""])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(
            "QTableWidget::item { padding: 6px; border-bottom: 1px solid rgba(128,128,140,0.30); }"
            "QTableWidget::item:selected { background: rgba(245,166,35,0.28); }")

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self):
        TableSpinner.show(self.table)
        try:
            self._listings = api_client.list_discovered_listings(only_new=True)
        except ApiError as e:
            TableSpinner.hide(self.table)
            handle_api_error(self, e, "خطا در دریافت یافته‌ها")
            return
        TableSpinner.hide(self.table)
        self._render()

    def _render(self):
        self.table.setRowCount(len(self._listings))
        for row, item in enumerate(self._listings):
            self.table.setItem(row, 0, QTableWidgetItem(item.get("title") or ""))
            self.table.setItem(row, 1, QTableWidgetItem(item.get("raw_address") or "—"))
            price = item.get("price")
            self.table.setItem(row, 2, QTableWidgetItem(f"{price:,} تومان" if price else "—"))
            self.table.setItem(row, 3, QTableWidgetItem(item.get("source") or ""))
            self.table.setItem(row, 4, QTableWidgetItem((item.get("posted_at") or "")[:10]))

            actions = QWidget()
            al = QHBoxLayout(actions)
            al.setContentsMargins(4, 0, 4, 0)

            add_btn = QPushButton("➕ افزودن به فایل‌ها")
            add_btn.setObjectName("chip")
            add_btn.clicked.connect(lambda _, lid=item["id"]: self._convert(lid))
            al.addWidget(add_btn)

            dismiss_btn = QPushButton("✖")
            dismiss_btn.setObjectName("chip")
            dismiss_btn.setToolTip("نادیده بگیر")
            dismiss_btn.clicked.connect(lambda _, lid=item["id"]: self._dismiss(lid))
            al.addWidget(dismiss_btn)

            self.table.setCellWidget(row, 5, actions)

    def _convert(self, listing_id: int):
        try:
            result = api_client.convert_discovery_listing(listing_id)
        except ApiError as e:
            handle_api_error(self, e, "خطا در تبدیل به فایل")
            return
        Toast.show(f"➕ فایل جدید ساخته شد (#{result.get('property_id')})")
        self.refresh()

    def _dismiss(self, listing_id: int):
        try:
            api_client.dismiss_discovery_listing(listing_id)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.refresh()