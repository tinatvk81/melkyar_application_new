from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import auth, properties, users, version, import_excel, property_images, reports
from app.core.config import settings

app = FastAPI(title="سامانه‌ی مدیریت فایل‌های ملکی")

app.include_router(auth.router)
app.include_router(properties.router)
app.include_router(property_images.router)
app.include_router(import_excel.router)
app.include_router(reports.router)
app.include_router(users.router)
app.include_router(version.router)

# پوشه‌ای که نصب‌کننده‌های exe نسخه‌های جدید در آن قرار می‌گیرند (بخش ۸ روادمپ)
app.mount("/static-installers", StaticFiles(directory="static_installers"), name="static-installers")


@app.get("/health")
def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}


# اجرا: uvicorn app.main:app --host 0.0.0.0 --port 8000
