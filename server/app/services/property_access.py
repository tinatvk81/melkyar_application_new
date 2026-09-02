from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.property import Property, PropertyStatus
from app.models.user import User, UserRole


def get_accessible_property(db: Session, current_user: User, property_id: int) -> Property:
    """
    همان قانون کلیدی دسترسی که در properties.py هم رعایت شده: مشاور فقط فایل
    خودش را می‌بیند، مدیر همه را. این‌جا هم استفاده می‌شود چون آپلود/حذف عکس هم
    باید همین محدودیت را رعایت کند (مشاور نباید بتواند عکس فایل مشاور دیگر را
    ببیند یا حذف کند).
    """
    q = db.query(Property).filter(Property.id == property_id, Property.status == PropertyStatus.active)
    if current_user.role != UserRole.admin:
        q = q.filter(Property.owner_agent_id == current_user.id)
    prop = q.first()
    if not prop:
        raise HTTPException(status_code=404, detail="فایل پیدا نشد یا دسترسی ندارید")
    return prop
