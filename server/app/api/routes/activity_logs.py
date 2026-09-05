from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.activity_log import ActivityLog
from app.models.user import User
from app.schemas.activity_log import ActivityLogRead, ActivityLogListResponse

router = APIRouter(prefix="/activity-logs", tags=["activity-logs"])

MAX_PAGE_SIZE = 200
DEFAULT_PAGE_SIZE = 50


@router.get("/", response_model=ActivityLogListResponse)
def list_activity_logs(
    entity_type: Optional[str] = None,
    days: int = 30,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """
    فقط برای مدیر: تاریخچه‌ی کامل عملیات (چه کسی، چه زمانی، چه کاری، روی چه چیزی).
    `days=0` یعنی بدون محدودیت زمانی (همه‌ی تاریخچه).
    """
    page = max(page, 1)
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)

    q = db.query(ActivityLog, User.full_name, User.username).join(User, ActivityLog.user_id == User.id)
    if entity_type:
        q = q.filter(ActivityLog.entity_type == entity_type)
    if days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        q = q.filter(ActivityLog.created_at >= cutoff)

    total = q.count()
    total_pages = max((total + page_size - 1) // page_size, 1)

    rows = (
        q.order_by(ActivityLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        ActivityLogRead(
            id=log.id,
            user_full_name=full_name,
            username=username,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            detail=log.detail,
            created_at=log.created_at,
        )
        for log, full_name, username in rows
    ]

    return ActivityLogListResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )
