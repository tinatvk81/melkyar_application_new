"""آپلود نصب‌کنندهٔ کلاینت (فقط مدیر) — برای مکانیزم آپدیت خودکار.
فایل exe ساخته‌شده را با همین endpoint روی هاست می‌گذاریم؛ چون static_installers
دیسک پایدار دارد، با هر دیپلوی نمی‌پرد."""
import os
import shutil

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import require_admin
from app.core.config import settings

router = APIRouter(prefix="/installers", tags=["installers"])

INSTALLER_DIR = "static_installers"


@router.post("/upload")
def upload_installer(file: UploadFile = File(...), _admin=Depends(require_admin)):
    if not (file.filename or "").lower().endswith(".exe"):
        raise HTTPException(400, "فایل باید نصب‌کنندهٔ exe باشد")
    os.makedirs(INSTALLER_DIR, exist_ok=True)
    # دقیقاً با نامی که /version به کلاینت‌ها اعلام می‌کند ذخیره می‌شود
    path = os.path.join(INSTALLER_DIR, settings.INSTALLER_FILENAME)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"ok": True, "filename": settings.INSTALLER_FILENAME, "size": os.path.getsize(path)}


@router.get("/list")
def list_installers(_admin=Depends(require_admin)):
    os.makedirs(INSTALLER_DIR, exist_ok=True)
    return {"files": os.listdir(INSTALLER_DIR), "expected": settings.INSTALLER_FILENAME}