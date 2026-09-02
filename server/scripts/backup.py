"""
استراتژی پشتیبان‌گیری (طراحی‌شده برای ۱۰٬۰۰۰+ فایل ملکی و رشد مداوم):

قانون ۳-۲-۱:
  - ۳ نسخه از داده
  - روی ۲ نوع رسانه‌ی مختلف (مثلاً: هارد داخلی سرور + هارد اکسترنال/فضای ابری)
  - ۱ نسخه خارج از محل دفتر (Offsite) — تا در صورت آتش‌سوزی/سرقت کل دفتر هم داده نابود نشود

این اسکریپت:
  ۱. یک pg_dump فشرده از کل دیتابیس می‌گیرد (شامل هر ۱۰٬۰۰۰+ رکورد ملکی)
  ۲. پوشه‌ی media (عکس‌های فایل‌ها) را هم zip می‌کند
  ۳. بک‌آپ‌ها را با چرخش (Rotation) نگه می‌دارد تا فضای دیسک پر نشود:
       - روزانه: ۱۴ روز اخیر نگه داشته می‌شود
       - هفتگی: ۸ هفته‌ی اخیر (هر یکشنبه) نگه داشته می‌شود
       - ماهانه: ۱۲ ماه اخیر (روز اول هر ماه) نگه داشته می‌شود

نحوه‌ی زمان‌بندی (روی ویندوز سرور دفتر):
  Task Scheduler > Create Task > Trigger: Daily at 03:00 AM (خارج از ساعت کاری)
  Action: "C:\\...\\venv\\Scripts\\python.exe" "C:\\...\\server\\scripts\\backup.py"

نکته‌ی حیاتی: این اسکریپت فقط نسخه‌ی *محلی* می‌سازد. برای رعایت «۱ نسخه‌ی
Offsite»، پوشه‌ی BACKUP_ROOT را با یکی از این روش‌ها هر شب بیرون از دفتر ببرید:
  - همگام‌سازی خودکار با یک سرویس ابری (rclone به سمت فضای ابری ایرانی مثل
    آروان‌کلاود/لیارا آبجکت استوریج، یا هر Object Storage دیگر)
  - یا فیزیکی: یک هارد اکسترنال که هفته‌ای یک‌بار جابه‌جا و از دفتر خارج می‌شود
"""
import os
import shutil
import subprocess
from datetime import datetime, date

# --- تنظیمات (با env واقعی خودتان جایگزین کنید) ---
POSTGRES_HOST = "localhost"
POSTGRES_PORT = "5432"
POSTGRES_DB = "realestate"
POSTGRES_USER = "realestate_app"
PGPASSWORD = os.environ.get("PGPASSWORD", "CHANGE_ME")  # از env بخوانید، هرگز هاردکد نکنید

MEDIA_DIR = os.path.join(os.path.dirname(__file__), "..", "media")
BACKUP_ROOT = os.environ.get("BACKUP_ROOT", r"D:\backups\realestate")  # روی درایو/دیسک جدا از سیستم اصلی


def run_backup():
    today = date.today()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    daily_dir = os.path.join(BACKUP_ROOT, "daily")
    os.makedirs(daily_dir, exist_ok=True)

    dump_path = os.path.join(daily_dir, f"db_{timestamp}.dump")
    media_zip_path = os.path.join(daily_dir, f"media_{timestamp}")

    env = os.environ.copy()
    env["PGPASSWORD"] = PGPASSWORD

    # فرمت custom پستگرس (فشرده + قابل ریستور انتخابی، بهتر از sql خام برای دیتابیس بزرگ)
    subprocess.run(
        [
            "pg_dump",
            "-h", POSTGRES_HOST,
            "-p", POSTGRES_PORT,
            "-U", POSTGRES_USER,
            "-Fc",
            "-f", dump_path,
            POSTGRES_DB,
        ],
        env=env,
        check=True,
    )
    print(f"[OK] دامپ دیتابیس ذخیره شد: {dump_path}")

    if os.path.isdir(MEDIA_DIR):
        shutil.make_archive(media_zip_path, "zip", MEDIA_DIR)
        print(f"[OK] بک‌آپ عکس‌ها ذخیره شد: {media_zip_path}.zip")

    # --- کپی به بایگانی هفتگی/ماهانه ---
    if today.weekday() == 6:  # یکشنبه (0=دوشنبه در پایتون... برای ایران با احتیاط تنظیم کنید)
        weekly_dir = os.path.join(BACKUP_ROOT, "weekly")
        os.makedirs(weekly_dir, exist_ok=True)
        shutil.copy2(dump_path, weekly_dir)

    if today.day == 1:
        monthly_dir = os.path.join(BACKUP_ROOT, "monthly")
        os.makedirs(monthly_dir, exist_ok=True)
        shutil.copy2(dump_path, monthly_dir)

    _rotate(daily_dir, keep=14)
    _rotate(os.path.join(BACKUP_ROOT, "weekly"), keep=8)
    _rotate(os.path.join(BACKUP_ROOT, "monthly"), keep=12)


def _rotate(folder: str, keep: int):
    if not os.path.isdir(folder):
        return
    files = sorted(
        (os.path.join(folder, f) for f in os.listdir(folder)),
        key=os.path.getmtime,
    )
    while len(files) > keep:
        oldest = files.pop(0)
        os.remove(oldest)
        print(f"[CLEANUP] فایل قدیمی حذف شد: {oldest}")


if __name__ == "__main__":
    run_backup()
