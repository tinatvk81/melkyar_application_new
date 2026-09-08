
راهنمای نصب، راه‌اندازی و تست — ملک‌یار (سرور: WSL / کلاینت: ویندوز)
معماری: سرور (FastAPI + PostgreSQL) داخل WSL اوبونتو اجرا می‌شود؛کلاینت (برنامهٔ دسکتاپ) روی ویندوز اجرا می‌شود و به 127.0.0.1:8000 وصل می‌شود(WSL2 پورت‌ها را به localhost ویندوز forward می‌کند).

گام ۰: پیش‌نیازها
WSL2 + اوبونتو — بررسی در PowerShell: wsl --status
داخل WSL: python3.12 --version و psql --version
روی ویندوز: Python 3.11+ از python.org با تیک Add to PATH — بررسی در CMD: python --version
مسیر پروژه: C:\Users\Tina\Desktop\app
گام ۱: دیتابیس (فقط بار اول — داخل WSL)
sudo service postgresql startsudo -u postgres psql
داخل psql:

CREATE DATABASE melkyar;CREATE USER melkyar_app WITH ENCRYPTED PASSWORD 'admin';GRANT ALL PRIVILEGES ON DATABASE melkyar TO melkyar_app;\q
گام ۲: سرور (داخل WSL)
وارد پروژه شو و محیط مجازی بساز:

cd /mnt/c/Users/Tina/Desktop/apppython3.12 -m venv venvsource venv/bin/activatecd server
نصب کتابخانه‌ها:

python -m pip install --upgrade pippip install -r requirements.txt
پوشه‌های لازم:

mkdir -p static_installers media logs
فایل .env — این ۵ خط باید با دیتابیس بخواند:

POSTGRES_DB=melkyarPOSTGRES_USER=melkyar_appPOSTGRES_PASSWORD=adminSECRET_KEY=<خروجی دستور زیر>DEBUG=true
تولید SECRET_KEY:

python3 -c "import secrets; print(secrets.token_urlsafe(48))"
ساخت جداول و کاربر مدیر:

alembic upgrade headpython scripts/init_admin.py
اجرای سرور (پنجره را باز نگه دارید):

uvicorn app.main:app --host 0.0.0.0 --port 8000
تست در مرورگر ویندوز: http://localhost:8000/health

گام ۳: کلاینت (روی ویندوز — CMD، نه WSL!)
cd C:\Users\Tina\Desktop\app\client 
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
در پنجرهٔ ورود ← «تنظیمات اتصال» ← آدرس: http://127.0.0.1:8000 ← تست اتصال ← ذخیره.

گام ۴: چک‌لیست تست
 ورود با حساب مدیر
 افزودن فایل جدید + نمایش در جدول + ویرایش با دابل‌کلیک
 تایپ دستی متراژ/اتاق با کیبورد فارسی
 امکانات دلخواه: افزودن و حذف مورد
 قیمت هر متر در معاملهٔ فروش خودکار محاسبه شود
 خروجی PDF با متن فارسی سالم
 ایمپورت اکسل: دانلود قالب ← پرکردن ← ایمپورت
 انتخاب عکس: دیالوگ ویندوزی (Desktop / Downloads / درایوها)
 ساخت مشاور + ورود با مشاور + جداسازی فایل‌ها
 قفل حساب: ۳ رمز اشتباه با کاربر مشاور ← پیام قفل ۲ دقیقه‌ای
عیب‌یابی
مشکل	راه‌حل
could not connect to server در alembic/سرور	sudo service postgresql start
No matching distribution found for PySide6==6.7.3	در client/requirements.txt به PySide6==6.10.3 تغییر دهید (Python 3.14 ویندوز)
کلاینت وصل نمی‌شود	داخل WSL: curl http://localhost:8000/health — اگر جواب داد، در کلاینت http://127.0.0.1:8000 بگذارید
پورت 8000 اشغال	uvicorn app.main:app --host 0.0.0.0 --port 8001
/docs باز نمی‌شود	DEBUG=true در .env (فقط برای تست)
بعد از ری‌استارت ویندوز	sudo service postgresql start + اجرای دوباره uvicorn