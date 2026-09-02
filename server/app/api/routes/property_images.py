from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.property_image import PropertyImage
from app.models.user import User
from app.services.property_access import get_accessible_property
from app.services.image_storage import (
    save_image_file, get_image_path, delete_image_file, ALLOWED_CONTENT_TYPES
)

router = APIRouter(prefix="/properties/{property_id}/images", tags=["property-images"])


@router.get("/")
def list_images(
    property_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    get_accessible_property(db, current_user, property_id)  # فقط برای بررسی دسترسی
    images = (
        db.query(PropertyImage)
        .filter(PropertyImage.property_id == property_id)
        .order_by(PropertyImage.created_at.asc())
        .all()
    )
    return [
        {
            "id": img.id,
            "original_filename": img.original_filename,
            "content_type": img.content_type,
            "created_at": img.created_at,
        }
        for img in images
    ]


@router.post("/")
async def upload_images(
    property_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_accessible_property(db, current_user, property_id)

    if len(files) > settings.MAX_IMAGES_PER_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail=f"حداکثر {settings.MAX_IMAGES_PER_UPLOAD} عکس در هر بار قابل آپلود است",
        )

    max_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    created = []
    for file in files:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(status_code=400, detail=f"فرمت «{file.content_type}» پشتیبانی نمی‌شود")

        content = await file.read()
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"فایل «{file.filename}» بزرگ‌تر از حد مجاز ({settings.MAX_IMAGE_SIZE_MB} مگابایت) است",
            )

        stored_filename = save_image_file(property_id, file.content_type, content)
        image = PropertyImage(
            property_id=property_id,
            stored_filename=stored_filename,
            original_filename=file.filename,
            content_type=file.content_type,
        )
        db.add(image)
        created.append(image)

    db.commit()
    return {"created": len(created)}


@router.get("/{image_id}/file")
def get_image_file(
    property_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    فایل عکس را فقط در صورتی برمی‌گرداند که کاربر به فایل ملکی مربوطه دسترسی داشته باشد
    (بر خلاف یک پوشه‌ی static عمومی که هرکسی لینک را داشته باشد می‌تواند ببیند).
    """
    get_accessible_property(db, current_user, property_id)
    image = (
        db.query(PropertyImage)
        .filter(PropertyImage.id == image_id, PropertyImage.property_id == property_id)
        .first()
    )
    if not image:
        raise HTTPException(status_code=404, detail="عکس پیدا نشد")

    path = get_image_path(property_id, image.stored_filename)
    return FileResponse(path, media_type=image.content_type)


@router.delete("/{image_id}")
def delete_image(
    property_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_accessible_property(db, current_user, property_id)
    image = (
        db.query(PropertyImage)
        .filter(PropertyImage.id == image_id, PropertyImage.property_id == property_id)
        .first()
    )
    if not image:
        raise HTTPException(status_code=404, detail="عکس پیدا نشد")

    delete_image_file(property_id, image.stored_filename)
    db.delete(image)
    db.commit()
    return {"ok": True}
