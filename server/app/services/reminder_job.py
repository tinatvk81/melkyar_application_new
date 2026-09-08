"""
یادآوری روزانه‌ی قراردادهای رو‌به‌اتمام به مشاور — نه به مالک/مستاجر، طبق
همان تصمیم روادمپ اولیه (بخش ۱۱): مشاور باید یادآوری بگیرد تا خودش با
مالک/مستاجر تماس بگیرد.
"""
import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.property import Property, PropertyStatus
from app.models.user import User, UserRole
from app.services.sms_service import send_sms

logger = logging.getLogger(__name__)


def build_reminder_message(agent_full_name: str, properties: list[Property]) -> str:
    lines = [f"سلام {agent_full_name}، {len(properties)} قرارداد شما به‌زودی تمام می‌شود:"]
    for p in properties:
        days_left = (p.contract_end_date - date.today()).days
        lines.append(f"- {p.city}، {p.address or 'بدون آدرس'} ({days_left} روز مانده)")
    return "\n".join(lines)


def run_daily_reminder_job(db: Session) -> dict:
    """
    برای هر مشاوری که شماره تلفن ثبت کرده و حداقل یک قرارداد فوری (طبق
    SMS_URGENT_DAYS_THRESHOLD) دارد، یک پیامک تجمیعی می‌فرستد (نه یک پیامک
    جدا برای هر فایل، تا مشاور با چند پیامک پشت‌سرهم آزرده نشود).

    خروجی یک گزارش است (چند مشاور بررسی شدند، چند پیامک فرستاده شد) — برای
    لاگ کردن و برای تست‌پذیر بودن، نه فقط side effect بی‌گزارش.
    """
    if not settings.SMS_ENABLED:
        logger.info("SMS_ENABLED=false است — کارِ یادآوری روزانه اجرا نشد")
        return {"enabled": False, "agents_checked": 0, "sms_sent": 0}

    cutoff = date.today() + timedelta(days=settings.SMS_URGENT_DAYS_THRESHOLD)

    agents = db.query(User).filter(User.role == UserRole.agent, User.is_active.is_(True)).all()

    sms_sent = 0
    for agent in agents:
        if not agent.phone:
            continue

        urgent_properties = (
            db.query(Property)
            .filter(
                Property.owner_agent_id == agent.id,
                Property.status == PropertyStatus.active,
                Property.contract_end_date.isnot(None),
                Property.contract_end_date <= cutoff,
            )
            .order_by(Property.contract_end_date.asc())
            .all()
        )
        if not urgent_properties:
            continue

        message = build_reminder_message(agent.full_name, urgent_properties)
        if send_sms(agent.phone, message):
            sms_sent += 1

    return {"enabled": True, "agents_checked": len(agents), "sms_sent": sms_sent}
