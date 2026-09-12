
# 🏠 ملک‌یار — سامانهٔ مدیریت فایل‌های ملکی (دسکتاپ چندکاربره)

**FastAPI + PostgreSQL** روی سرور دفتر (یا WSL) ← **PySide6** روی سیستم هر مشاور.
هیچ رمز دیتابیسی روی لپ‌تاپ مشاور نیست؛ همه‌چیز با JWT و HTTP.

## ✨ قابلیت‌ها
- مدیریت فایل‌های ملکی (فروش/پیش‌خرید/اجاره/رهن) با تاریخ شمسی، امکانات دلخواه، گالری عکس
- هشدار فایل تکراری/مشابه، جست‌وجوی زنده با هایلایت، فیلترهای آمادهٔ قابل‌گسترش (با تأیید مدیر)
- **حسابداری پورسانت**: قولنامه، قطعی با گارد، پرداخت/دریافت با عکس رسید، مانده هر نفر، PDF صورتحساب و **قرارداد رسمی با قالب قابل‌ویرایش**
- **درخواست مشتری + تطبیق خودکار** با فایل‌های فعال (ایزوله برای هر مشاور)
- **پیگیری روزمره** با تاریخ شمسی + ساعت، و **زنگ اطلاع‌یه** هوشمند (سررسیدها، معامله‌ها، درخواست‌ها)
- **چت داخلی** مدیر↔مشاور
- داشبورد آماری با نمودار، بایگانی + انقضای خودکار با تأیید مالک فایل
- امنیت: JWT، قفل حساب پس از تلاش‌های ناموفق، ابطال فوری نشست‌ها، لاگ ساختاریافته
- پشتیبان‌گیری خودکار روزانه

## 🚀 شروع سریع
راهنمای گام‌به‌گام کامل (نصب، دیتابیس، اجرا، چک‌لیست تست، عیب‌یابی): **[INSTALL_AND_TEST.md](INSTALL_AND_TEST.md)**

خلاصه:
```bash
# سرور (WSL/لینوکس)
cd server && pip install -r requirements.txt
alembic upgrade head && python scripts/init_admin.py
uvicorn app.main:app --host 0.0.0.0 --port 8000

# کلاینت (ویندوز)
cd client && pip install -r requirements.txt && python main.py
```

## 🧱 معماری
```
client/  (PySide6 — فقط HTTP+JWT به سرور)
server/  (FastAPI + SQLAlchemy + Alembic + PostgreSQL)
  app/api/routes/      auth, properties, property_images, users, reports,
                       deals, client_requests, follow_ups, notifications,
                       filter_presets, chat, version, import_excel
  app/models|schemas|services/
  alembic/             مهاجرت‌ها
  contract_template.txt  قالب قرارداد رسمی (قابل ویرایش بدون کد)
```

## 🔐 نکات استقرار واقعی
- `.env` را هرگز کامیت نکنید؛ `DEBUG=false` و `SECRET_KEY` قوی
- رمز دیتابیس قوی؛ پورت سرور فقط روی شبکهٔ دفتر
- بکاپ روزانه + تست دوره‌ای بازیابی
```
