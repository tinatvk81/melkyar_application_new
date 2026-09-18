from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton,
)
import settings_manager
from ui.styles import apply_persian_rtl_style


class FontSizeDialog(QDialog):
    """اسلایدر اندازه‌ی فونت — ۱۲ تا ۲۴ پیکسل، پیش‌نمایش زنده، انصراف = برگشت."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("اندازه فونت")
        self.setMinimumWidth(360)
        self._original = settings_manager.get_font_size()

        self._preview_label = QLabel()
        self._preview_label.setAlignment(Qt.AlignCenter)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(12, 24)
        self._slider.setValue(self._original)
        self._slider.setTickPosition(QSlider.TicksBelow)
        self._slider.setTickInterval(1)
        self._slider.valueChanged.connect(self._on_slide)

        hint = QLabel("اسلایدر را بکش — اندازه بلافاصله اعمال می‌شود.\n"
                      "«ذخیره» اندازه را نگه می‌دارد، «انصراف» به حالت قبل برمی‌گرداند.")
        hint.setAlignment(Qt.AlignCenter)

        save_btn = QPushButton("ذخیره")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("انصراف")
        cancel_btn.clicked.connect(self.reject)

        btns = QHBoxLayout()
        btns.addStretch()
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)

        lay = QVBoxLayout(self)
        lay.addWidget(self._preview_label)
        lay.addWidget(self._slider)
        lay.addWidget(hint)
        lay.addLayout(btns)
        self._update_preview_label()

    def _update_preview_label(self):
        self._preview_label.setText(f"متن نمونه: ۱۲,۵۰۰,۰۰۰ تومان — اندازه {self._slider.value()}")

    def _on_slide(self, value: int):
        self._update_preview_label()
        self._apply(value)

    def _apply(self, size: int):
        apply_persian_rtl_style(QApplication.instance(),
                                mode=settings_manager.get_theme(), font_size=size)

    def accept(self):
        settings_manager.set_font_size(self._slider.value())
        super().accept()

    def reject(self):
        self._apply(self._original)  # برگرداندن پیش‌نمایش به اندازه‌ی قبلی
        super().reject()