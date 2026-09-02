"""
ویجت انتخاب تاریخ شمسی — چون کاربران این برنامه مشاور املاک ایرانی هستند،
تاریخ قرارداد و تحویل باید با تقویم شمسی وارد/نمایش داده شود، نه میلادی.
دیتابیس و API همچنان تاریخ میلادی استاندارد (YYYY-MM-DD) نگه می‌دارند —
تبدیل فقط در همین لایه‌ی نمایش (UI) اتفاق می‌افتد.
"""
from datetime import date

import jdatetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSpinBox, QPushButton, QLabel


class JalaliDateEdit(QWidget):
    def __init__(self, allow_empty: bool = True):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.allow_empty = allow_empty
        self._has_value = False

        today = jdatetime.date.today()

        self.year_spin = QSpinBox()
        self.year_spin.setRange(1370, 1450)
        self.year_spin.setValue(today.year)

        self.month_spin = QSpinBox()
        self.month_spin.setRange(1, 12)
        self.month_spin.setValue(today.month)

        self.day_spin = QSpinBox()
        self.day_spin.setRange(1, 31)
        self.day_spin.setValue(today.day)

        today_btn = QPushButton("امروز")
        today_btn.clicked.connect(self.set_today)

        clear_btn = QPushButton("خالی")
        clear_btn.setVisible(allow_empty)
        clear_btn.clicked.connect(self.clear)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("سال:"))
        layout.addWidget(self.year_spin)
        layout.addWidget(QLabel("ماه:"))
        layout.addWidget(self.month_spin)
        layout.addWidget(QLabel("روز:"))
        layout.addWidget(self.day_spin)
        layout.addWidget(today_btn)
        layout.addWidget(clear_btn)
        self.setLayout(layout)

        self._has_value = not allow_empty  # اگر تاریخ اجباری است (مثل پایان قرارداد اجاره)، از ابتدا مقدار دارد
        self._set_enabled(self._has_value)

    def _set_enabled(self, enabled: bool):
        for w in (self.year_spin, self.month_spin, self.day_spin):
            w.setEnabled(enabled)

    def set_today(self):
        today = jdatetime.date.today()
        self.year_spin.setValue(today.year)
        self.month_spin.setValue(today.month)
        self.day_spin.setValue(today.day)
        self._has_value = True
        self._set_enabled(True)

    def clear(self):
        self._has_value = False
        self._set_enabled(False)

    def set_gregorian_date(self, g_date):
        """g_date: datetime.date میلادی یا None"""
        if g_date is None:
            self.clear()
            return
        j = jdatetime.date.fromgregorian(date=g_date)
        self.year_spin.setValue(j.year)
        self.month_spin.setValue(j.month)
        self.day_spin.setValue(j.day)
        self._has_value = True
        self._set_enabled(True)

    def get_gregorian_date(self):
        """خروجی: datetime.date میلادی برای ارسال به API، یا None اگر خالی گذاشته شده"""
        if not self._has_value:
            return None
        try:
            j = jdatetime.date(self.year_spin.value(), self.month_spin.value(), self.day_spin.value())
            return j.togregorian()
        except ValueError:
            return None  # روز نامعتبر برای آن ماه (مثل ۳۱ ام آبان)

    def get_iso_string(self):
        g = self.get_gregorian_date()
        return g.isoformat() if g else None
