from datetime import date

import jdatetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QSizePolicy

from ui.widgets import PersianSpinBox
import settings_manager


class JalaliDateEdit(QWidget):
    """تاریخ شمسی فشرده به شکل ۱۴۰۵/۰۷/۲۶ — در دیالوگ‌های باریک هم بدون بریدگی جا می‌شود.
    «خالی» یعنی بدون تاریخ (None)؛ هر تغییر دستی بعد از آن دوباره معتبر می‌شود."""

    def __init__(self, allow_empty: bool = True):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.allow_empty = allow_empty
        self._loading = True

        _f = max(1.0, settings_manager.get_font_size() / 13)
        year_w, small_w = int(62 * _f), int(46 * _f)

        today = jdatetime.date.today()
        self.year_spin = PersianSpinBox(minimum=1300, maximum=1500)
        self.month_spin = PersianSpinBox(minimum=1, maximum=12)
        self.day_spin = PersianSpinBox(minimum=1, maximum=31)

        # علت باگ قبلی: استایل سراسری «min-width: 90px» باعث می‌شد سه اسپین + برچسب‌ها + دکمه‌ها
        # در دیالوگ باریک جا نشوند و ویجت بیرون بزند. استایل محلیِ زیر آن حد را کوچک می‌کند.
        self.year_spin.setMinimumWidth(year_w)
        self.year_spin.setStyleSheet(f"QAbstractSpinBox {{ min-width: {year_w}px; padding: 4px 4px; }}")
        self.month_spin.setMinimumWidth(small_w)
        self.month_spin.setStyleSheet(f"QAbstractSpinBox {{ min-width: {small_w}px; padding: 4px 4px; }}")
        self.day_spin.setMinimumWidth(small_w)
        self.day_spin.setStyleSheet(f"QAbstractSpinBox {{ min-width: {small_w}px; padding: 4px 4px; }}")

        self.year_spin.setValue(today.year)
        self.month_spin.setValue(today.month)
        self.day_spin.setValue(today.day)

        today_btn = QPushButton("امروز")
        today_btn.setToolTip("انتخاب تاریخ امروز")
        clear_btn = QPushButton("خالی")
        clear_btn.setToolTip("بدون تاریخ")
        clear_btn.setVisible(allow_empty)
        today_btn.clicked.connect(self.set_today)
        clear_btn.clicked.connect(self.clear)

        sep1 = QLabel("/")
        sep2 = QLabel("/")
        for l in (sep1, sep2):
            l.setStyleSheet("background: transparent;")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.addWidget(self.year_spin, 1)
        lay.addWidget(sep1)
        lay.addWidget(self.month_spin)
        lay.addWidget(sep2)
        lay.addWidget(self.day_spin)
        lay.addSpacing(8)
        lay.addWidget(today_btn)
        lay.addWidget(clear_btn)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._has_value = not allow_empty
        self.year_spin.valueChanged.connect(self._touched)
        self.month_spin.valueChanged.connect(self._touched)
        self.day_spin.valueChanged.connect(self._touched)
        self._loading = False

    def _touched(self):
        if not self._loading:
            self._has_value = True

    def set_today(self):
        self._loading = True
        today = jdatetime.date.today()
        self.year_spin.setValue(today.year)
        self.month_spin.setValue(today.month)
        self.day_spin.setValue(today.day)
        self._loading = False
        self._has_value = True

    def clear(self):
        self._has_value = False

    def set_gregorian_date(self, g_date):
        if g_date is None:
            self.clear()
            return
        self._loading = True
        j = jdatetime.date.fromgregorian(date=g_date)
        self.year_spin.setValue(j.year)
        self.month_spin.setValue(j.month)
        self.day_spin.setValue(j.day)
        self._loading = False
        self._has_value = True

    def get_gregorian_date(self):
        if not self._has_value:
            return None
        try:
            return jdatetime.date(self.year_spin.value(), self.month_spin.value(), self.day_spin.value()).togregorian()
        except ValueError:
            return None

    def get_iso_string(self):
        g = self.get_gregorian_date()
        return g.isoformat() if g else None