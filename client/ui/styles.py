"""
راست‌به‌چپ کردن کل برنامه + بارگذاری فونت فارسی.
فونت پیشنهادی: Vazirmatn (رایگان و متن‌باز) — فایل .ttf را در
client/resources/fonts/Vazirmatn-Regular.ttf قرار دهید.
دانلود از: https://github.com/rastikerdar/vazirmatn (فایل‌های release)
"""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtWidgets import QApplication

FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "resources", "fonts", "Vazirmatn-Regular.ttf")


def apply_persian_rtl_style(app: QApplication):
    # --- جهت راست‌به‌چپ برای کل برنامه (منو، دکمه‌ها، چیدمان فرم‌ها) ---
    app.setLayoutDirection(Qt.RightToLeft)

    # --- فونت فارسی ---
    if os.path.exists(FONT_PATH):
        font_id = QFontDatabase.addApplicationFont(FONT_PATH)
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            app.setFont(QFont(families[0], 10))
    else:
        # اگر فونت را هنوز اضافه نکرده‌اید، حداقل یک فونت پیش‌فرض خواناتر بگذارید
        app.setFont(QFont("Tahoma", 10))
