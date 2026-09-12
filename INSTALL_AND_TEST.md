## سه بخش: مستندات نهایی + گیت + نظر صادقانه دربارهٔ Docker/استقرار/انتشار

---

# ۱) فایل کامل جدید: `INSTALL_AND_TEST.md`

```markdown
# 🏠 ملک‌یار — راهنمای نصب، راه‌اندازی و تست

سامانهٔ مدیریت فایل‌های ملکی: **FastAPI + PostgreSQL** (سرور) و **PySide6** (کلاینت دسکتاپ).
سرور روی WSL/لینوکس اجرا می‌شود؛ کلاینت روی ویندوز هر مشاور و فقط با HTTP به سرور وصل می‌شود.

---

## گام ۰: پیش‌نیازها

| محل | نیاز |
|---|---|
| WSL (اوبونتو) | Python 3.11+ (این سیستم: python3.12)، PostgreSQL 15+ |
| ویندوز | Python 3.11+ از python.org با تیک **Add to PATH** |
| مسیر پروژه | `C:\Users\Tina\Desktop\app` (در WSL: `/mnt/c/Users/Tina/Desktop/app`) |

## گام ۱: دیتابیس (داخل WSL — فقط بار اول)

```bash
sudo service postgresql start      # یا با systemd: sudo systemctl start postgresql
sudo -u postgres psql
```
```sql
CREATE DATABASE melkyar;
CREATE USER melkyar_app WITH ENCRYPTED PASSWORD 'admin';
GRANT ALL PRIVILEGES ON DATABASE melkyar TO melkyar_app;
\q
```
> رمز `admin` فقط برای تست محلی است.

## گام ۲: سرور (داخل WSL)

```bash
cd /mnt/c/Users/Tina/Desktop/app
python3.12 -m venv venv
source venv/bin/activate
cd server
python -m pip install --upgrade pip
pip install -r requirements.txt
mkdir -p static_installers media/logs media/receipts logs
```

فایل `.env` (فقط بار اول) — کلید را با
`python3 -c "import secrets; print(secrets.token_urlsafe(48))"` بساز:

```env
POSTGRES_DB=melkyar
POSTGRES_USER=melkyar_app
POSTGRES_PASSWORD=admin
SECRET_KEY=<کلید-تولیدشده>
DEBUG=true
```

```bash
alembic upgrade head        # ساخت/به‌روزرسانی همه‌ی جدول‌ها
python scripts/init_admin.py   # ساخت کاربر مدیر (نام کاربری/رمز دلخواه)
uvicorn app.main:app --host 0.0.0.0 --port 8000   # پنجره باز بماند
```

تست در مرورگر ویندوز: `http://localhost:8000/health` → `{"status":"ok",...}`

## گام ۳: کلاینت (روی ویندوز — CMD، نه WSL!)

```
cd C:\Users\Tina\Desktop\app\client
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

در پنجرهٔ ورود → «تنظیمات اتصال» → آدرس `http://127.0.0.1:8000` → تست اتصال → ذخیره → ورود با حساب مدیر.

> اگر فیلترشکن/پروکسی سیستم روشن است، برنامه خودش localhost را مستقیم وصل می‌شود (NO_PROXY داخل کد فعال است).

## گام ۴: چک‌لیست تست کامل

**فایل‌ها**
- [ ] افزودن/ویرایش فایل با تایپ فارسی در همهٔ فیلدهای عددی و تاریخ‌ها
- [ ] قیمت هر متر خودکار در فروش؛ امکانات دلخواه چیپی؛ اعتبارسنجی تلفن
- [ ] هشدار فایل مشابه (تلفن/شهر+آدرس) قبل از ذخیره
- [ ] بندانگشتی عکس در فهرست؛ دابل‌کلیک روی عکس = گالری؛ گالری بعد از ذخیرهٔ فایل جدید
- [ ] جست‌وجوی زنده (Ctrl+F)، هایلایت متن، چیپ‌های آماده، «سایر +» (پیشنهاد/تأیید مدیر، حذف با درخواست)

**حسابداری پورسانت (مدیر)**
- [ ] ثبت معامله برای مشاور یا خود مدیر (درصد دستی یا پیش‌فرض)
- [ ] قطعی با تأیید + پیام تکرار؛ «بازگشت به در جریان» برای اصلاح
- [ ] پرداخت به مشاور / دریافت از مشاور + تاریخ + توضیح + عکس رسید (+ افزودن/تعویض بعدی)
- [ ] مانده‌ها (کارکرد − خالص پرداخت) + PDF صورتحساب، مانده‌ها و **قولنامه رسمی** (قالب قابل‌ویرایش: `server/contract_template.txt`)

**بایگانی و انقضا**
- [ ] بایگانی غیرفعال/فروخته‌شده + بازگردانی
- [ ] اسکن فایل‌های قدیمی → اطلاع‌یه به مالک → تأیید انقضا یا نگه‌داشتن

**درخواست مشتری**
- [ ] ثبت درخواست + «فایل‌های منطبق» خودکار (مشاور فقط فایل‌های خودش)

**پیگیری و اطلاع‌یه**
- [ ] پیگیری با تاریخ شمسی + ساعت؛ فیلتر امروز/عقب‌افتاده/آینده؛ تیک انجام
- [ ] زنگ اطلاع‌یه: پیگیری‌های امروز/عقب‌افتاده، قطعی/پرداخت برای مشاور، پیشنهاد/درخواست حذف فیلتر برای مدیر
- [ ] مدیر: دیدن اطلاع‌یه‌های هر مشاور از کمبوی پنجرهٔ زنگ

**چت داخلی**
- [ ] گفت‌وگوی مدیر↔مشاور با حباب‌ها، شمارش خوانده‌نشده در زنگ، خواندن خودکار با باز کردن گفت‌وگو

**کاربران**
- [ ] ساخت مشاور، فعال/غیرفعال جدا، ریست رمز، تلفن پیامکی، درصد پورسانت به تفکیک نوع معامله
- [ ] قفل حساب: ۳ رمز اشتباه مشاور = قفل ۲ دقیقه (مدیر نامحدود)

**داشبورد**
- [ ] کارت‌ها کلیک‌پذیر، نمودار معامله‌ها و پورسانت (مدیر)، کارت عکس‌دارها

## عیب‌یابی

| مشکل | راه‌حل |
|---|---|
| `could not connect` در سرور | `sudo service postgresql start` |
| دیالوگ باز-بسته شد | Traceback را از CMD ویندوز بردارید — علت دقیق همان‌جاست |
| ۴۰۱ «نشست نامعتبر» | لاگین مجدد (توکن ۸ ساعته منقضی یا ریست‌رمز شده) |
| ۵۰۰ | `tail -n 60 logs/*.log` در پوشهٔ server |
| کلاینت وصل نشد | curl داخل WSL به `/health`؛ آدرس کلاینت `http://127.0.0.1:8000` |
| پایتون 3.14 ویندوز | در client/requirements.txt: `PySide6==6.10.3` |
| بعد از ری‌استارت ویندوز | postgres و uvicorn را دوباره روشن کنید (systemd فعال: `sudo systemctl enable --now cron postgresql`) |

## پشتیبان‌گیری
هر شب ۲ بامداد خودکار در `/opt/melkyar-backups` (نگه‌داری ۱۴ روز):
```bash
(sudo crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/melkyar-backup.sh") | sudo crontab -
```
بازیابی: `gunzip -c FILE.sql.gz | sudo -u postgres psql melkyar`
```
