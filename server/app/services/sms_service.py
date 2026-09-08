"""
سرویس ارسال پیامک — برای یادآوری خودکار قراردادهای رو‌به‌اتمام به مشاور.

نکته‌ی مهم: این ماژول به یک حساب واقعی نزد یک سرویس‌دهنده‌ی پیامک ایرانی نیاز
دارد. **من نمی‌توانم ارسال واقعی پیامک را از این‌جا تست کنم** چون نیاز به
اعتبار واقعی (API Key پولی) دارد که در اختیار من نیست. آنچه واقعاً تست شده:
منطق ساخت درخواست، مدیریت خطا، و گروه‌بندی/فیلتر یادآوری‌ها (با mock کردن
درخواست HTTP در تست‌ها) — نه ارسال واقعی روی خط.

سرویس‌دهنده‌ی پیش‌فرض این‌جا **کاوه‌نگار** (Kavenegar) است چون یکی از
پرکاربردترین‌ها در ایران است و API ساده‌ای دارد. برای فعال‌سازی واقعی:
۱. در https://kavenegar.com ثبت‌نام کنید و یک API Key بگیرید.
۲. در فایل .env سرور: SMS_ENABLED=true و SMS_API_KEY=<کلید شما>
۳. اختیاری: SMS_SENDER_LINE اگر خط اختصاصی دارید.

اگر می‌خواهید از سرویس‌دهنده‌ی دیگری استفاده کنید (ملی‌پیامک و غیره)، فقط
کافی است تابع send_sms این فایل را با API آن سرویس‌دهنده جایگزین کنید —
بقیه‌ی برنامه (reminder_job.py) فقط با send_sms() کار دارد، نه با جزئیات
پیاده‌سازی یک سرویس‌دهنده‌ی خاص.
"""
import logging

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

KAVENEGAR_SEND_URL = "https://api.kavenegar.com/v1/{api_key}/sms/send.json"


class SmsError(Exception):
    pass


def send_sms(phone: str, message: str) -> bool:
    """
    یک پیامک ارسال می‌کند. اگر SMS_ENABLED خاموش باشد یا API Key تنظیم نشده
    باشد، بی‌سروصدا False برمی‌گرداند (تا اجرای برنامه به‌خاطر نبودِ یک حساب
    پیامک متوقف نشود) — فقط در فایل لاگ این وضعیت ثبت می‌شود.
    """
    if not settings.SMS_ENABLED:
        logger.info("ارسال پیامک غیرفعال است (SMS_ENABLED=false) — پیامک به %s ارسال نشد", phone)
        return False
    if not settings.SMS_API_KEY:
        logger.warning("SMS_ENABLED=true است ولی SMS_API_KEY خالی است — پیامک ارسال نشد")
        return False

    url = KAVENEGAR_SEND_URL.format(api_key=settings.SMS_API_KEY)
    params = {"receptor": phone, "message": message}
    if settings.SMS_SENDER_LINE:
        params["sender"] = settings.SMS_SENDER_LINE

    try:
        resp = requests.get(url, params=params, timeout=10)
    except requests.RequestException as e:
        logger.error("خطا در اتصال به سرویس پیامک: %s", e)
        return False

    if resp.status_code != 200:
        logger.error("سرویس پیامک خطا داد (HTTP %s): %s", resp.status_code, resp.text[:300])
        return False

    logger.info("پیامک با موفقیت به %s ارسال شد", phone)
    return True
