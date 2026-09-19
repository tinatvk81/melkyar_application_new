"""ماشین‌حساب رهن ↔ اجاره — ضریب پیش‌فرض ۳۰ (هر ۱۰ هزار اجاره = ۳۰۰ هزار ودیعه)
قابل تغییر در تنظیمات (settings.json کلید rent_mortgage_factor)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QLineEdit, QComboBox,
)

import settings_manager
from ui.widgets import MoneyLineEdit

FA = {"mortgage_to_rent": "رهن ← اجاره", "rent_to_mortgage": "اجاره ← رهن"}


def get_factor() -> float:
    s = settings_manager.load_settings()
    try:
        f = float(s.get("rent_mortgage_factor") or 30)
    except (TypeError, ValueError):
        f = 30.0
    return max(1.0, f)


class RentMortgageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("ماشین‌حساب رهن ↔ اجاره")
        self.setMinimumWidth(420)

        form = QFormLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("رهن را به اجاره تبدیل کن", "mortgage_to_rent")
        self.mode_combo.addItem("اجاره را به رهن تبدیل کن", "rent_to_mortgage")
        form.addRow("حالت:", self.mode_combo)

        self.amount_input = MoneyLineEdit("مبلغ (تومان)")
        form.addRow("مبلغ ورودی:", self.amount_input)

        self.result_label = QLabel("—")
        self.result_label.setStyleSheet("font-size: 15px; font-weight: 800; color: #f5a623; background: transparent;")
        self.result_label.setAlignment(Qt.AlignCenter)
        form.addRow("نتیجه:", self.result_label)

        self.mode_combo.currentIndexChanged.connect(self._calc)
        self.amount_input.editingFinished.connect(self._calc)

        btns = QHBoxLayout()
        btns.addStretch()
        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.accept)
        btns.addWidget(close_btn)

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(QLabel(f"ضریب فعلی: هر {int(get_factor()):,} تومان ودیعه = ۱۰ هزار تومان اجاره "
                             f"(قابل تغییر در settings.json — کلید rent_mortgage_factor)"))
        lay.addLayout(btns)

    def _calc(self):
        try:
            amount = self.amount_input.value() or 0
        except ValueError:
            self.result_label.setText("مبلغ نامعتبر")
            return
        f = get_factor()
        if not amount:
            self.result_label.setText("—")
            return
        if self.mode_combo.currentData() == "mortgage_to_rent":
            rent = amount / f  # تومان در ماه
            self.result_label.setText(f"اجارهٔ معادل: {int(round(rent)):,} تومان در ماه")
        else:
            deposit = amount * f
            self.result_label.setText(f"ودیعهٔ معادل: {int(round(deposit)):,} تومان")