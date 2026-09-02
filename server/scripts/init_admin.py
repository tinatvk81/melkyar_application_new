"""
یک‌بار اجرا شود تا اولین کاربر مدیر ساخته شود.

نکته‌ی مهم: این اسکریپت دیگر جدول‌ها را خودش نمی‌سازد؛ ساخت/به‌روزرسانی
جدول‌های دیتابیس حالا به‌طور کامل با Alembic انجام می‌شود (چون autogenerate و
downgrade/upgrade آن واقعاً روی یک دیتابیس واقعی تست شده و درست کار می‌کند).
قبل از اجرای این اسکریپت حتماً یک‌بار این را اجرا کنید:
    alembic upgrade head

اجرای این اسکریپت از داخل پوشه‌ی server (با venv فعال):
    python scripts/init_admin.py
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import inspect

from app.db.session import SessionLocal, engine
from app.models.user import User, UserRole
from app.core.security import hash_password

# بررسی این‌که migration اجرا شده، تا کاربر با یک خطای گنگ روبه‌رو نشود
if "users" not in inspect(engine).get_table_names():
    print("جدول‌های دیتابیس هنوز ساخته نشده‌اند.")
    print("ابتدا این دستور را اجرا کنید:  alembic upgrade head")
    sys.exit(1)

db = SessionLocal()
username = input("نام کاربری مدیر: ").strip()
full_name = input("نام و نام‌خانوادگی: ").strip()
password = input("رمز عبور: ").strip()

if db.query(User).filter(User.username == username).first():
    print("این نام کاربری از قبل وجود دارد.")
else:
    admin = User(
        username=username,
        full_name=full_name,
        hashed_password=hash_password(password),
        role=UserRole.admin,
    )
    db.add(admin)
    db.commit()
    print(f"کاربر مدیر «{username}» با موفقیت ساخته شد.")

db.close()
