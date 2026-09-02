"""
تنظیمات سرور — این فایل مقادیر حساس (رمز دیتابیس، کلید امنیتی) را از فایل .env
می‌خواند. فایل .env هرگز نباید به مشتریان (کلاینت‌ها) فرستاده شود یا در Git قرار بگیرد.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- دیتابیس مرکزی (فقط روی همین سرور اجرا می‌شود) ---
    POSTGRES_HOST: str = "localhost"   # پستگرس فقط از خودِ همین سرور قابل دسترسی است
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "realestate"
    POSTGRES_USER: str = "realestate_app"
    POSTGRES_PASSWORD: str = "CHANGE_ME"

    # --- امنیت / JWT ---
    SECRET_KEY: str = "CHANGE_ME_TO_A_LONG_RANDOM_STRING"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # ۸ ساعت؛ بعد از این باید دوباره لاگین کند

    # --- شبکه ---
    # آدرسی که کلاینت‌ها روی شبکه‌ی محلی دفتر با آن به سرور وصل می‌شوند
    SERVER_BIND_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    # --- نسخه‌ی برنامه (برای مکانیزم آپدیت خودکار کلاینت‌ها) ---
    APP_VERSION: str = "1.0.0"
    INSTALLER_FILENAME: str = "RealEstateApp-Setup-1.0.0.exe"

    # --- ذخیره‌سازی عکس‌های فایل‌های ملکی ---
    # مسیر نسبت به پوشه‌ی server (کنار پوشه‌ی app). همین پوشه باید در بک‌آپ (scripts/backup.py) لحاظ شود.
    MEDIA_ROOT: str = "media"
    MAX_IMAGE_SIZE_MB: int = 8
    MAX_IMAGES_PER_UPLOAD: int = 10

    class Config:
        env_file = ".env"


settings = Settings()
