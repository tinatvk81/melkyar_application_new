"""ماشین‌حساب رهن ↔ اجاره — ضریب پیش‌فرض از settings.json (کلید rent_mortgage_factor)
ولی در همان پنجره قابل ویرایش است (مثلاً ضریب متفاوت برای مناطق مختلف)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QComboBox, QLineEdit,
)

import settings_manager
from ui.widgets import MoneyLineEdit


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
        self.setMinimumWidth(440)

        form = QFormLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("رهن را به اجاره تبدیل کن", "mortgage_to_rent")
        self.mode_combo.addItem("اجاره را به رهن تبدیل کن", "rent_to_mortgage")
        form.addRow("حالت:", self.mode_combo)

        self.amount_input = MoneyLineEdit("مبلغ (تومان)")
        form.addRow("مبلغ ورودی:", self.amount_input)

        self.factor_input = QLineEdit(str(int(get_factor())))
        self.factor_input.setToolTip("هر این‌قدر تومان ودیعه = ۱۰ هزار تومان اجارهٔ ماهانه.\n"
                                     "برای منطقه‌های مختلف همین‌جا عوضش کن — ذخیرهٔ دائمی در settings.json")
        self.factor_input.editingFinished.connect(self._calc)
        form.addRow("ضریب تبدیل:", self.factor_input)

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
        lay.addWidget(QLabel("فرمول: اجارهٔ ماهانه = ودیعه ÷ ضریب (بر حسب تومان)"))
        lay.addLayout(btns)

    def _calc(self):
        try:
            amount = self.amount_input.value() or 0
        except ValueError:
            self.result_label.setText("مبلغ نامعتبر")
            return
        try:
            factor = float(self.factor_input.text().strip() or get_factor())
            if factor < 1:
                factor = get_factor()
        except (TypeError, ValueError):
            self.result_label.setText("ضریب نامعتبر")
            return
        if not amount:
            self.result_label.setText("—")
            return
        if self.mode_combo.currentData() == "mortgage_to_rent":
            self.result_label.setText(f"اجارهٔ معادل: {int(round(amount / factor)):,} تومان در ماه")
        else:
            self.result_label.setText(f"ودیعهٔ معادل: {int(round(amount * factor)):,} تومان")