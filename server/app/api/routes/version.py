from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["version"])


@router.get("/version")
def get_version():
    """
    کلاینت هنگام باز شدن این آدرس را چک می‌کند. اگر نسخه‌اش قدیمی‌تر بود،
    لینک دانلود نصب‌کننده‌ی جدید را (که مستقیم از همین سرور سرو می‌شود) نمایش می‌دهد.
    برای انتشار نسخه‌ی جدید، کافی است:
    ۱) فایل exe جدید را در پوشه‌ی server/static_installers قرار دهید
    ۲) APP_VERSION و INSTALLER_FILENAME را در .env آپدیت کنید و سرور را ری‌استارت کنید
    """
    return {
        "version": settings.APP_VERSION,
        "installer_url": f"/static-installers/{settings.INSTALLER_FILENAME}",
    }
