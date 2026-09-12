from datetime import date

import jdatetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel

from ui.widgets import PersianSpinBox


class JalaliDateEdit(QWidget):
    """تاریخ شمسی — همیشه فعال؛ تایپ/چرخش دستی همان لحظه مقدار را معتبر می‌کند.
    «خالی» یعنی بدون تاریخ (None)؛ هر تغییر دستی بعد از آن دوباره معتبر می‌شود."""

    def __init__(self, allow_empty: bool = True):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.allow_empty = allow_empty
        self._loading = True

        today = jdatetime.date.today()
        self.year_spin = PersianSpinBox(minimum=1300, maximum=1500)
        self.year_spin.setValue(today.year)
        self.month_spin = PersianSpinBox(minimum=1, maximum=12)
        self.month_spin.setValue(today.month)
        self.day_spin = PersianSpinBox(minimum=1, maximum=31)
        self.day_spin.setValue(today.day)
        for sp, w in ((self.year_spin, 95), (self.month_spin, 75), (self.day_spin, 75)):
            sp.setMinimumWidth(w)

        today_btn = QPushButton("امروز")
        today_btn.clicked.connect(self.set_today)
        clear_btn = QPushButton("خالی")
        clear_btn.setVisible(allow_empty)
        clear_btn.clicked.connect(self.clear)

        lay = QHBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel("سال:")); lay.addWidget(self.year_spin)
        lay.addWidget(QLabel("ماه:")); lay.addWidget(self.month_spin)
        lay.addWidget(QLabel("روز:")); lay.addWidget(self.day_spin)
        lay.addWidget(today_btn); lay.addWidget(clear_btn)
        self.setLayout(lay)

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