from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QGroupBox, QRadioButton, QFormLayout,
)
import settings_manager
from ui.styles import apply_persian_rtl_style


class SettingsDialog(QDialog):
    """تنظیمات برنامه: تم + اندازه فونت.
    اسلایدر بلافاصله پیش‌نمایش می‌دهد؛ «انصراف» همه‌چیز را به حالت قبل برمی‌گرداند."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("تنظیمات")
        self.setMinimumWidth(430)

        self._orig_theme = settings_manager.get_theme()
        self._orig_font = settings_manager.get_font_size()

        box = QGroupBox("نمایش")
        form = QFormLayout(box)

        theme_row = QHBoxLayout()
        self._rb_dark = QRadioButton("تیره")
        self._rb_light = QRadioButton("روشن")
        (self._rb_dark if self._orig_theme == "dark" else self._rb_light).setChecked(True)
        self._rb_dark.toggled.connect(self._apply_preview)
        theme_row.addWidget(self._rb_dark)
        theme_row.addWidget(self._rb_light)
        theme_row.addStretch()
        form.addRow("تم:", theme_row)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(12, 24)
        self._slider.setValue(self._orig_font)
        self._slider.setTickPosition(QSlider.TicksBelow)
        self._slider.setTickInterval(1)
        self._slider.valueChanged.connect(self._apply_preview)
        self._value_label = QLabel(f"{self._orig_font} پیکسل")
        font_row = QHBoxLayout()
        font_row.addWidget(self._slider, 1)
        font_row.addWidget(self._value_label)
        form.addRow("اندازه فونت:", font_row)

        self._preview = QLabel("پیش‌نمایش: آپارتمان ۸۵ متری — ۴,۵۰۰,۰۰۰,۰۰۰ تومان")
        self._preview.setAlignment(Qt.AlignCenter)
        self._preview.setWordWrap(True)

        hint = QLabel("اندازه‌ی پیشنهادی: ۱۳ تا ۱۶ پیکسل. اندازه‌های بزرگ‌تر مخصوص مانیتور بزرگ است؛ "
                      "عرض سایدبار خودکار تنظیم می‌شود ولی بهتر است پنجره را هم بزرگ‌تر کنید.")
        hint.setWordWrap(True)

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
        lay.addWidget(box)
        lay.addWidget(self._preview)
        lay.addWidget(hint)
        lay.addLayout(btns)

    def _apply_preview(self, *_):
        self._value_label.setText(f"{self._slider.value()} پیکسل")
        apply_persian_rtl_style(QApplication.instance(), mode=self._current_theme(),
                                font_size=self._slider.value())

    def _current_theme(self) -> str:
        return "dark" if self._rb_dark.isChecked() else "light"

    def accept(self):
        settings_manager.set_theme(self._current_theme())
        settings_manager.set_font_size(self._slider.value())
        super().accept()

    def reject(self):
        apply_persian_rtl_style(QApplication.instance(), mode=self._orig_theme,
                                font_size=self._orig_font)
        super().reject()