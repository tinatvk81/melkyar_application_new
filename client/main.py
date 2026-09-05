import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from ui.styles import apply_persian_rtl_style
from ui.login_window import LoginWindow
from ui.main_window import MainWindow
from ui.urgent_renewals_dialog import UrgentRenewalsDialog, URGENT_DAYS_THRESHOLD
from updater import check_for_update
from api_client import api_client, ApiError
from session import register_session_expired_handler, reset_session_expired_flag


def main():
    app = QApplication(sys.argv)
    apply_persian_rtl_style(app)

    window_holder = {}

    def show_login_window():
        login_window = LoginWindow(on_success=show_main_window)
        window_holder["login"] = login_window
        login_window.show()

    def show_main_window():
        reset_session_expired_flag()  # نشست جدید موفق شد؛ آماده برای دفعه‌ی بعد هم باش
        if "login" in window_holder:
            window_holder["login"].close()
        window_holder["main"] = MainWindow()
        window_holder["main"].show()
        check_for_update(window_holder["main"])
        check_urgent_renewals(window_holder["main"])

    def check_urgent_renewals(main_window):
        """
        قبلاً تب «قراردادهای رو‌به‌اتمام» کاملاً منفعل بود — کاربر باید خودش
        یادش می‌ماند بازش کند. حالا بلافاصله بعد از ورود، اگر قراردادی خیلی
        نزدیک به پایان باشد (کمتر از یک هفته)، یک هشدار برجسته نشان داده
        می‌شود، نه این‌که به یادآوریِ خودِ کاربر متکی باشیم.
        """
        try:
            urgent = api_client.upcoming_renewals(days=URGENT_DAYS_THRESHOLD)
        except ApiError:
            return  # اگر سرور موقتاً در دسترس نبود، مانع باز شدن برنامه نشو
        if urgent:
            dialog = UrgentRenewalsDialog(urgent, on_view_all=main_window.switch_to_renewals_tab)
            dialog.exec()

    def handle_session_expired():
        """
        وقتی هر درخواستی به سرور با کد ۴۰۱ برگردد (توکن منقضی شده یا حساب
        غیرفعال/ریست‌رمز شده)، این تابع صدا زده می‌شود: پنجره‌ی اصلی بسته
        می‌شود، توکن پاک می‌شود، و کاربر با یک پیام روشن به صفحه‌ی ورود
        برمی‌گردد — به‌جای این‌که در همان صفحه یک خطای گنگ ببیند.
        """
        if "main" in window_holder and window_holder["main"] is not None:
            window_holder["main"].close()
            window_holder["main"] = None
        api_client.logout()
        QMessageBox.information(
            None, "پایان نشست", "نشست شما پایان یافته یا اعتبار آن از بین رفته است. لطفاً دوباره وارد شوید."
        )
        show_login_window()

    register_session_expired_handler(handle_session_expired)

    show_login_window()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
