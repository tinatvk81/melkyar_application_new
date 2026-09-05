"""
مدیریت مرکزی انقضای نشست (Session Expiry).

قبلاً: وقتی توکن JWT منقضی می‌شد یا به هر دلیلی دیگر معتبر نبود (مثلاً مدیر
رمز کاربر را ریست کرده یا حسابش را غیرفعال کرده)، سرور با کد ۴۰۱ پاسخ می‌داد
و کاربر در هر صفحه‌ای که بود، فقط یک پیام خطای گنگ («نام کاربری یا رمز عبور
اشتباه است» یا مشابه آن) می‌دید — که گمراه‌کننده است چون او اصلاً چیزی تایپ
نکرده، فقط نشستش تمام شده.

الان: همه‌ی صفحات به‌جای QMessageBox مستقیم بعد از `except ApiError`، از تابع
`handle_api_error()` همین فایل استفاده می‌کنند. این تابع اگر تشخیص دهد خطا
واقعاً انقضای نشست بوده (کد ۴۰۱)، یک پیام روشن نشان می‌دهد و کاربر را به
صفحه‌ی ورود برمی‌گرداند — یک‌بار، نه یک پیام برای هر درخواست ناموفق هم‌زمان.
"""
from PySide6.QtWidgets import QMessageBox

_on_session_expired = None
_session_expired_shown = False


def register_session_expired_handler(callback):
    """main.py این را یک‌بار در ابتدای برنامه صدا می‌زند."""
    global _on_session_expired
    _on_session_expired = callback


def reset_session_expired_flag():
    """بعد از ورود موفق دوباره صدا زده می‌شود تا دفعه‌ی بعد هم این مکانیزم کار کند."""
    global _session_expired_shown
    _session_expired_shown = False


def _trigger_session_expired():
    global _session_expired_shown
    if _session_expired_shown:
        return  # اگر چند درخواست هم‌زمان ۴۰۱ گرفتند، فقط یک‌بار نشان بده
    _session_expired_shown = True
    if _on_session_expired:
        _on_session_expired()


def handle_api_error(parent, error, title="خطا", critical=False):
    """
    این تابع را به‌جای QMessageBox.warning/critical مستقیم بعد از
    `except ApiError as e:` صدا بزنید. اگر خطا انقضای نشست بود (۴۰۱)، خودش
    کاربر را مدیریت می‌کند و دیگر لازم نیست شما پیامی نشان دهید.
    """
    if getattr(error, "status_code", None) == 401:
        _trigger_session_expired()
        return
    box_fn = QMessageBox.critical if critical else QMessageBox.warning
    box_fn(parent, title, str(error))
