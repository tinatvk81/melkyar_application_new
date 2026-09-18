"""آپلود نصب‌کنندهٔ کلاینت (فقط مدیر) — نسخهٔ تکه‌تکه برای شبکه‌های ناپایدار.
/chunk: هر تکه با شمارهٔ خودش ذخیره می‌شود؛ /finalize تکه‌ها را کنار هم می‌چیند.
هر دو مسیر در دیسک پایدار static_installers می‌مانند."""
import os
import shutil

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.deps import require_admin
from app.core.config import settings

router = APIRouter(prefix="/installers", tags=["installers"])

INSTALLER_DIR = "static_installers"


@router.post("/upload")
def upload_installer(file: UploadFile = File(...), _admin=Depends(require_admin)):
    """آپلود یک‌جا (برای شبکه‌های خوب) — همان رفتار قبلی."""
    if not (file.filename or "").lower().endswith(".exe"):
        raise HTTPException(400, "فایل باید نصب‌کنندهٔ exe باشد")
    os.makedirs(INSTALLER_DIR, exist_ok=True)
    path = os.path.join(INSTALLER_DIR, settings.INSTALLER_FILENAME)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"ok": True, "filename": settings.INSTALLER_FILENAME, "size": os.path.getsize(path)}


def _chunk_dir() -> str:
    d = os.path.join(INSTALLER_DIR, ".chunks")
    os.makedirs(d, exist_ok=True)
    return d


@router.post("/chunk")
def upload_chunk(index: int = Form(...), file: UploadFile = File(...), _admin=Depends(require_admin)):
    d = _chunk_dir()
    path = os.path.join(d, f"part_{index:04d}")
    size = 0
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        size = f.tell()
    return {"ok": True, "index": index, "size": size}


@router.post("/finalize")
def finalize(count: int = Form(...), _admin=Depends(require_admin)):
    d = _chunk_dir()
    final = os.path.join(INSTALLER_DIR, settings.INSTALLER_FILENAME)
    total = 0
    with open(final, "wb") as out:
        for i in range(count):
            part = os.path.join(d, f"part_{i:04d}")
            if not os.path.exists(part):
                raise HTTPException(400, f"تکهٔ {i} پیدا نشد — دوباره همان را بفرست")
            with open(part, "rb") as pf:
                shutil.copyfileobj(pf, out)
            total += os.path.getsize(part)
    if total < 1_000_000:
        os.remove(final)
        raise HTTPException(400, "حجم نهایی غیرمنطقی است — آپلود ناقص بوده")
    for i in range(count):
        p = os.path.join(d, f"part_{i:04d}")
        if os.path.exists(p):
            os.remove(p)
    return {"ok": True, "filename": settings.INSTALLER_FILENAME, "size": total}


@router.get("/list")
def list_installers(_admin=Depends(require_admin)):
    os.makedirs(INSTALLER_DIR, exist_ok=True)
    return {"files": os.listdir(INSTALLER_DIR), "expected": settings.INSTALLER_FILENAME}