import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import require_admin
from app.services.backup_service import build_backup_bytes, backup_dir, prune

router = APIRouter(prefix="/backups", tags=["backups"])


@router.post("/run")
def run_backup(_admin=Depends(require_admin)):
    name = f"melkyar-{datetime.now().strftime('%Y%m%d-%H%M')}.json.gz"
    path = os.path.join(backup_dir(), name)
    try:
        data = build_backup_bytes()
    except Exception as e:
        raise HTTPException(500, f"بکاپ ناموفق: {e}")
    with open(path, "wb") as f:
        f.write(data)
    prune()
    return {"ok": True, "filename": name, "size": os.path.getsize(path)}


@router.get("/list")
def list_backups(_admin=Depends(require_admin)):
    out = []
    for f in sorted(os.listdir(backup_dir()), reverse=True):
        if f.endswith(".json.gz"):
            out.append({"filename": f, "size": os.path.getsize(os.path.join(backup_dir(), f))})
    return out


@router.get("/download/{filename}")
def download_backup(filename: str, _admin=Depends(require_admin)):
    if "/" in filename or "\\" in filename or not filename.endswith(".json.gz"):
        raise HTTPException(400, "نام فایل نامعتبر")
    path = os.path.join(backup_dir(), filename)
    if not os.path.exists(path):
        raise HTTPException(404, "بکاپ پیدا نشد")
    return FileResponse(path, filename=filename, media_type="application/gzip")