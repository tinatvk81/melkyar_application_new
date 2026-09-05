from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget, QTableWidgetItem
)

URGENT_DAYS_THRESHOLD = 7  # این آستانه با تب «قراردادهای رو‌به‌اتمام» (که ۳۰ روزه است) فرق دارد؛
                            # این‌جا فقط موارد واقعاً فوری (کمتر از یک هفته) هشدار داده می‌شوند


class UrgentRenewalsDialog(QDialog):
    """
    بعد از ورود، اگر قراردادی خیلی نزدیک به پایان باشد (کمتر از ۷ روز)، این
    دیالوگ بلافاصله نشان داده می‌شود — به‌جای این‌که کاربر مجبور باشد خودش
    تب «قراردادهای رو‌به‌اتمام» را باز کند و یادش بماند که چک کند.
    """

    def __init__(self, renewals: list[dict], on_view_all):
        super().__init__()
        self.on_view_all = on_view_all
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("⚠️ قراردادهای فوری")
        self.resize(560, 320)

        title = QLabel(f"{len(renewals)} قرارداد ظرف {URGENT_DAYS_THRESHOLD} روز آینده پایان می‌یابد:")
        title.setStyleSheet("font-weight: bold; font-size: 13px; color: #b02a2a;")

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["شهر", "آدرس", "روز باقی‌مانده", "تلفن مالک"])
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        today = date.today()
        table.setRowCount(len(renewals))
        for row, r in enumerate(renewals):
            days_left = ""
            if r.get("contract_end_date"):
                end_date = date.fromisoformat(r["contract_end_date"])
                days_left = str((end_date - today).days)
            table.setItem(row, 0, QTableWidgetItem(r.get("city", "")))
            table.setItem(row, 1, QTableWidgetItem(r.get("address") or ""))
            table.setItem(row, 2, QTableWidgetItem(days_left))
            table.setItem(row, 3, QTableWidgetItem(r.get("owner_phone") or ""))

        view_all_btn = QPushButton("مشاهده‌ی همه‌ی قراردادهای رو‌به‌اتمام")
        view_all_btn.clicked.connect(self.handle_view_all)
        close_btn = QPushButton("بعداً")
        close_btn.clicked.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.addWidget(view_all_btn)
        btn_row.addWidget(close_btn)

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(table)
        layout.addLayout(btn_row)
        self.setLayout(layout)

    def handle_view_all(self):
        self.accept()
        self.on_view_all()
