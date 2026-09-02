"""
مکانیزم آپدیت (بخش ۸ روادمپ): چون همه‌ی کلاینت‌ها همیشه به سرور مرکزی دفتر
وصل می‌شوند، خودِ همان سرور منبع نسخه‌ی جدید هم هست — نیازی به سرویس آپدیت
اینترنتی جداگانه نیست.

روند کار:
۱. هنگام باز شدن برنامه، از /version سرور نسخه‌ی فعلی سرور را می‌گیریم.
۲. اگر با APP_VERSION محلی فرق داشت، به کاربر پیام می‌دهیم و لینک دانلود
   نصب‌کننده‌ی جدید (که مستقیم از همان سرور سرو می‌شود) را می‌دهیم.
۳. برای انتشار نسخه‌ی جدید، فقط کافی است ادمین فایل exe جدید را در پوشه‌ی
   server/static_installers بگذارد و APP_VERSION را در .env سرور آپدیت کند —
   نیازی نیست هیچ لپ‌تاپی را دستی جمع کنید.
"""
import webbrowser

from PySide6.QtWidgets import QMessageBox

from config import SERVER_URL, APP_VERSION
from api_client import api_client, ApiError


def check_for_update(parent=None):
    try:
        info = api_client.get_server_version()
    except ApiError:
        return  # سرور در دسترس نبود؛ بی‌سروصدا رد شو، مانع باز شدن برنامه نشو

    server_version = info.get("version")
    if server_version and server_version != APP_VERSION:
        box = QMessageBox(parent)
        box.setWindowTitle("نسخه‌ی جدید موجود است")
        box.setText(
            f"نسخه‌ی نصب‌شده‌ی شما: {APP_VERSION}\n"
            f"نسخه‌ی جدید در دسترس: {server_version}\n\n"
            "برای دریافت نسخه‌ی جدید، دکمه‌ی زیر را بزنید."
        )
        download_btn = box.addButton("دانلود نسخه‌ی جدید", QMessageBox.AcceptRole)
        box.addButton("بعداً", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() == download_btn:
            webbrowser.open(f"{SERVER_URL}{info['installer_url']}")
