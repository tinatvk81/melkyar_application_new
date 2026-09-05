import io

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.excel_import_service import import_workbook
from app.services.excel_template import build_template_workbook
from app.services.activity_log_service import log_activity

router = APIRouter(prefix="/properties", tags=["excel-import"])


@router.get("/import-template")
def download_import_template():
    content = build_template_workbook()
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=import-template.xlsx"},
    )


@router.post("/import")
async def import_properties_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="فقط فایل اکسل (.xlsx) پذیرفته می‌شود")

    file_bytes = await file.read()
    try:
        # فایل‌های وارد شده به نام همان کاربری که Import را انجام می‌دهد ثبت می‌شوند
        new_properties, errors, duplicates = import_workbook(file_bytes, owner_agent_id=current_user.id, db=db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if new_properties:
        db.add_all(new_properties)
        db.commit()
        log_activity(
            db, current_user.id, "import_excel", "property",
            detail=f"{len(new_properties)} فایل ثبت شد، {len(errors)} خطا، {len(duplicates)} تکراری نادیده گرفته شد",
        )

    return {
        "created": len(new_properties),
        "error_count": len(errors),
        "errors": errors[:200],  # از انباشته شدن گزارش خیلی طولانی جلوگیری می‌کند
        "duplicate_count": len(duplicates),
        "duplicates": duplicates[:200],
    }
