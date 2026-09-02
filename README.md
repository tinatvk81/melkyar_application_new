# سامانه‌ی مدیریت فایل‌های ملکی (دسکتاپ، چندکاربره)

معماری: **PostgreSQL** (فقط روی سرور مرکزی دفتر) ← **FastAPI** (لایه‌ی API، روی همان سرور) ← **PySide6** (اپ دسکتاپ روی سیستم هر مشاور، فقط با HTTP به سرور وصل می‌شود، هیچ رمز دیتابیسی روی لپ‌تاپ مشاور ذخیره نمی‌شود).

جزئیات کامل تصمیمات و دلایل در فایل `roadmap-v2.md` است. این فایل فقط دستورهای اجرایی است.

---

## ۱. پیش‌نیازها (روی سیستمی که سرور روی آن نصب می‌شود)

1. Python 3.11 یا بالاتر
2. PostgreSQL 15+ (نصب و در حال اجرا، فقط روی `localhost`)
3. ساخت دیتابیس و کاربر اختصاصی در PostgreSQL:
   ```sql
   CREATE DATABASE realestate;
   CREATE USER realestate_app WITH ENCRYPTED PASSWORD 'یک-رمز-قوی';
   GRANT ALL PRIVILEGES ON DATABASE realestate TO realestate_app;
   ```

## ۲. ساخت venv خصوصی برای سرور

```bash
cd realestate-app/server
python -m venv venv

# فعال‌سازی venv:
# ویندوز (cmd):
venv\Scripts\activate.bat
# ویندوز (PowerShell):
venv\Scripts\Activate.ps1
# لینوکس/مک:
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

سپس فایل `.env.example` را کپی کنید و مقداردهی کنید:
```bash
cp .env.example .env
# .env را باز کنید و POSTGRES_PASSWORD و SECRET_KEY واقعی را بگذارید
```

ساخت جدول‌های دیتابیس با Alembic (این مرحله را واقعاً روی یک PostgreSQL واقعی تست
کردم — هم upgrade و هم downgrade درست کار می‌کنند، شامل تایپ‌های Enum پستگرس):
```bash
alembic upgrade head
```
هر بار که مدل‌ها (`app/models/*.py`) را تغییر دادید، یک migration جدید بسازید:
```bash
alembic revision --autogenerate -m "توضیح کوتاه تغییر"
alembic upgrade head
```

ساخت اولین کاربر مدیر (بعد از `alembic upgrade head`):
```bash
python scripts/init_admin.py
```

اجرای سرور (روی شبکه‌ی محلی دفتر در دسترس است، نه از اینترنت بیرون):
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

مستندات خودکار API (برای تست سریع endpointها در مرورگر همان سرور):
`http://localhost:8000/docs`

---

## ۳. ساخت venv خصوصی برای کلاینت (روی سیستم توسعه، یا هر لپ‌تاپ مشاور)

```bash
cd realestate-app/client
python -m venv venv
venv\Scripts\activate.bat        # یا معادل آن طبق بخش بالا

pip install --upgrade pip
pip install -r requirements.txt
```

قبل از اجرا، آدرس سرور را در `client/config.py` تنظیم کنید:
```python
SERVER_URL = "http://192.168.1.10:8000"   # IP واقعی سیستم سرور دفتر
```

فونت فارسی Vazirmatn را دانلود کنید و در مسیر زیر بگذارید:
```
client/resources/fonts/Vazirmatn-Regular.ttf
```
(از https://github.com/rastikerdar/vazirmatn — بخش Releases، فایل‌های ttf)

اجرای برنامه:
```bash
python main.py
```

---

## ۴. ساخت نصب‌کننده‌ی exe برای پخش به مشاوران (فاز بعدی)

```bash
cd realestate-app/client
pip install -r requirements-dev.txt
pyinstaller --noconsole --onefile --name RealEstateApp main.py
```
فایل خروجی در `dist/RealEstateApp.exe` است. این فایل را در پوشه‌ی
`server/static_installers/` روی سرور کپی کنید تا مکانیزم آپدیت خودکار
(`GET /version`) بتواند آن را به کلاینت‌های قدیمی‌تر معرفی کند.

---

## ۵. بک‌آپ خودکار (روی سیستم سرور)

```bash
cd realestate-app/server
venv\Scripts\activate.bat
python scripts/backup.py
```
این را در Windows Task Scheduler به‌صورت روزانه (مثلاً ساعت ۳ بامداد) زمان‌بندی کنید.
جزئیات کامل استراتژی در کامنت‌های بالای همان فایل و در `roadmap-v2.md` بخش ۸ است.

---

## ۶. ساختار پوشه‌ها

```
realestate-app/
├── server/                  # فقط روی سیستم مرکزی دفتر اجرا می‌شود
│   ├── app/
│   │   ├── core/            # تنظیمات، امنیت (هش، JWT)
│   │   ├── db/               # اتصال دیتابیس
│   │   ├── models/            # مدل‌های SQLAlchemy (User, Property, PropertyImage, ActivityLog)
│   │   ├── schemas/            # مدل‌های Pydantic ورودی/خروجی API
│   │   ├── services/            # منطق: import/export اکسل، PDF، ذخیره‌ی عکس، دسترسی
│   │   ├── resources/fonts/       # Vazirmatn (برای PDF فارسی)
│   │   ├── api/routes/          # auth.py, properties.py, property_images.py, users.py, reports.py, version.py
│   │   └── main.py               # نقطه‌ی ورود FastAPI
│   ├── alembic/                    # migration های دیتابیس (تست‌شده روی PostgreSQL واقعی)
│   │   └── versions/
│   ├── alembic.ini
│   ├── scripts/
│   │   ├── init_admin.py         # ساخت اولین مدیر (بعد از alembic upgrade head)
│   │   └── backup.py              # بک‌آپ خودکار روزانه
│   ├── media/                       # عکس‌های فایل‌های ملکی (باید در بک‌آپ لحاظ شود)
│   ├── static_installers/          # نصب‌کننده‌های exe نسخه‌های جدید این‌جا قرار می‌گیرند
│   ├── requirements.txt
│   └── .env.example
└── client/                    # روی سیستم/لپ‌تاپ هر مشاور نصب می‌شود
    ├── ui/
    │   ├── login_window.py
    │   ├── main_window.py
    │   ├── property_form.py
    │   ├── property_gallery_dialog.py
    │   ├── import_excel_dialog.py
    │   ├── user_form_dialog.py
    │   ├── jalali_date_edit.py
    │   └── styles.py             # راست‌به‌چپ + فونت فارسی
    ├── resources/fonts/           # Vazirmatn (از قبل بارگذاری شده)
    ├── api_client.py                # ارتباط با سرور (توکن فقط در RAM)
    ├── updater.py                    # چک نسخه‌ی جدید
    ├── config.py                      # فقط آدرس سرور
    ├── main.py
    ├── requirements.txt
    └── requirements-dev.txt            # + PyInstaller
```

---

## ۷. وضعیت فعلی این اسکلت (چه چیزی کار می‌کند، چه چیزی باقی مانده)

**آماده و قابل اجرا:**
- ورود با نام کاربری/رمز (JWT)، تفکیک نقش مدیر/مشاور
- فهرست فایل‌ها (با فیلتر خودکار سمت سرور: مشاور فقط فایل خودش)
- **فرم کامل افزودن/ویرایش فایل ملکی** (`client/ui/property_form.py`): فیلدهای مشترک
  + فیلدهای اختصاصی هر نوع معامله (فروش/پیش‌خرید/اجاره/رهن‌کامل) که با انتخاب
  نوع معامله خودکار عوض می‌شوند، همراه با **تاریخ شمسی** برای تاریخ تحویل/پایان قرارداد
  (`client/ui/jalali_date_edit.py`)
- دکمه‌های افزودن/ویرایش/غیرفعال‌سازی فایل + دابل‌کلیک روی ردیف برای ویرایش سریع
- تب قراردادهای رو‌به‌اتمام (ماژول یادآوری)
- مدیریت کاربران برای مدیر (`client/ui/user_form_dialog.py` + بخش `UserManagementTab`):
  ساخت حساب مشاور/مدیر جدید، غیرفعال/فعال کردن با یک دکمه (متن دکمه خودکار بین این دو حالت
  عوض می‌شود)، ریست رمز عبور — همه با ابطال فوری توکن‌های نشست باز آن کاربر (طبق تصمیم امنیتی
  بخش ۴ roadmap-v2.md)
- **گالری تصاویر** (`server/app/api/routes/property_images.py` + `client/ui/property_gallery_dialog.py`):
  آپلود چند عکس هم‌زمان، نمایش thumbnail، حذف تک‌تک عکس‌ها. عکس‌ها روی دیسک سرور در
  `server/media/properties/{id}/` با نام تصادفی (uuid) ذخیره می‌شوند (نه در دیتابیس، تا حجم
  دیتابیس و بک‌آپ‌گیری سنگین نشود). هر درخواست دیدن/حذف عکس همان قانون دسترسی مشاور/مدیر
  فایل ملکی مربوطه را چک می‌کند (بر خلاف یک پوشه‌ی static عمومی که هرکسی لینک را داشته باشد
  می‌تواند ببیند) — این پوشه از قبل در `scripts/backup.py` لحاظ شده است.
- **گزارش‌ها و خروجی PDF/اکسل** (`server/app/services/pdf_export.py`, `excel_export.py`,
  `server/app/api/routes/reports.py`): خروجی PDF/اکسل از فهرست فایل‌های قابل‌مشاهده‌ی کاربر
  (با همان محدودیت دسترسی مشاور/مدیر)، و برای مدیر یک تب «گزارش عملکرد مشاوران» با تعداد فایل
  هر مشاور به تفکیک نوع معامله + خروجی PDF همان گزارش. **PDF فارسی به‌درستی رندر می‌شود**
  (حروف به‌هم‌چسبیده و راست‌به‌چپ) چون از `arabic-reshaper` + `python-bidi` + فونت Vazirmatn
  استفاده شده — این ترکیب را واقعاً تست کردم و خروجی را به تصویر تبدیل کردم تا مطمئن شوم درست
  چاپ می‌شود.

**نکته‌ی فونت:** فایل واقعی `Vazirmatn-Regular.ttf` (رایگان، مجوز SIL OFL) از قبل در
`client/resources/fonts/` و `server/app/resources/fonts/` قرار داده شده — دیگر نیازی به دانلود
دستی نیست.
- **Import اکسل** (`server/app/services/excel_import_service.py` + `client/ui/import_excel_dialog.py`):
  دانلود قالب نمونه با ۴ شیت (فروش/پیش‌خرید/اجاره/رهن_کامل) + شیت راهنما، آپلود فایل تکمیل‌شده،
  گزارش دقیق ردیف‌به‌ردیف خطاها (با شماره‌ی ردیف واقعی در اکسل) بدون متوقف‌شدن کل Import —
  تست شده با داده‌ی واقعی و ردیف‌های خراب عمدی، هم مسیر موفق و هم مسیر خطا درست کار می‌کند.
- راست‌به‌چپ کامل + بارگذاری فونت فارسی
- مکانیزم چک نسخه‌ی جدید
- اسکریپت بک‌آپ با چرخش روزانه/هفتگی/ماهانه

- **Alembic migration** (`server/alembic/`): جدول‌ها دیگر با `create_all` ساخته نمی‌شوند.
  این را واقعاً روی یک PostgreSQL واقعی نصب کردم و تست کردم — `alembic upgrade head` تمام
  ۴ جدول (users, properties, activity_logs, property_images) + ایندکس‌ها را درست می‌سازد،
  و `alembic downgrade base` هم درست پاک می‌کند (شامل حذف صریح تایپ‌های Enum پستگرس که
  Alembic به‌طور پیش‌فرض فراموش می‌کند حذف کند — این باگ را واقعاً گرفتم و در migration
  اولیه دستی درستش کردم).
- **رفع یک باگ واقعی سازگاری نسخه:** ترکیب `passlib==1.7.4` با نسخه‌های جدید `bcrypt` (۴.۱+)
  خطای «password cannot be longer than 72 bytes» می‌دهد چون passlib به یک ویژگی داخلی
  bcrypt نیاز دارد که در نسخه‌های جدید حذف شده. در `requirements.txt` نسخه‌ی `bcrypt==4.0.1`
  صریحاً پین شده تا این مشکل پیش نیاید (این را هم واقعاً روی سیستم بازتولید و رفع کردم).

**باقی‌مانده برای فازهای بعدی (طبق roadmap-v2.md):** هیچ‌کدام — همه‌ی موارد این roadmap
پیاده‌سازی و تست شدند. آخرین مورد هم همین بود:

- **پنل فیلتر پیشرفته** (`client/ui/property_filter_panel.py` + `apply_filters()` در `properties.py`):
  فیلتر بر اساس شهر، منطقه، نوع معامله، بازه‌ی متراژ، حداقل تعداد اتاق، آسانسور/پارکینگ،
  و **بازه‌ی قیمت** — با وجود این‌که قیمت داخل ستون JSONB و با اسم متفاوت برای هر نوع معامله
  ذخیره شده (`price`/`total_price`/`deposit_full`/`monthly_rent`)، یک عبارت SQL با
  `COALESCE` ساخته شده که همه‌ی این‌ها را به‌عنوان «مبلغ» در نظر می‌گیرد. همین فیلترها را
  می‌توان مستقیم به خروجی PDF/اکسل هم پاس داد (یک تابع `apply_filters` مشترک بین فهرست و
  export استفاده می‌شود) تا خروجی همیشه دقیقاً با چیزی که کاربر فیلتر کرده یکی باشد.

**باگ‌های واقعی که در این فاز پیدا و رفع کردم (با تست مستقیم روی PostgreSQL و FastAPI واقعی):**
- فیلتر بازه‌ی قیمت روی JSONB را با داده‌ی واقعی تست کردم (چند فایل با مبلغ‌های مختلف ساختم و
  چک کردم فیلتر `min_price`/`max_price` درست کار می‌کند).
- **باگ جدی در Content-Disposition:** اسم فایل‌های دانلودی (PDF/اکسل) اولش فارسی بود
  (مثلاً `فهرست-فایل-ها.pdf`)، ولی هدرهای HTTP فقط کاراکترهای Latin-1 قبول می‌کنند و این باعث
  کرش کامل سرور (خطای ۵۰۰) هنگام دانلود هر خروجی می‌شد. این را با تست واقعی HTTP گرفتم و اسم
  فایل‌های دانلودی را انگلیسی کردم (محتوای داخل فایل همچنان کاملاً فارسی است، فقط اسم فایل).

---

## نسخه‌ی ۳ (roadmap-v3.md) — در حال پیاده‌سازی

**۱. صفحه‌بندی واقعی فهرست فایل‌ها ✅ (انجام شد):**
نسخه‌ی قبلی یک `.limit(500)` هاردکد داشت که در مقیاس ۱۰٬۰۰۰+ فایل باعث می‌شد
فایل‌های بعد از ۵۰۰ اُم بی‌صدا از دید مدیر پنهان بمانند — نه خطایی، نه پیامی.
حالا `GET /properties/` پارامترهای `page` و `page_size` (حداکثر ۲۰۰) می‌پذیرد
و `total`, `total_pages` را هم برمی‌گرداند. **این را با ۶۵۰ رکورد واقعی روی
PostgreSQL تست کردم:** با `page_size` پیش‌فرض ۵۰، دقیقاً ۱۳ صفحه محاسبه شد،
صفحه‌ی آخر درست ۵۰ آیتم داد، و درخواست `page_size=1000` درست در سقف ۲۰۰ محدود
شد. کلاینت (`PropertyListTab`) حالا دکمه‌های «صفحه‌ی قبل/بعد» و برچسب
«صفحه X از Y — تعداد کل: N» دارد؛ تغییر فیلتر خودکار به صفحه‌ی ۱ برمی‌گردد.

باقی موارد roadmap-v3.md (آرشیو فایل غیرفعال، ثبت ActivityLog، جستجوی آزاد،
مرتب‌سازی، تنظیمات خارجی سرور، مدیریت انقضای نشست، قفل هم‌زمان، جلوگیری از
Import تکراری، لاگ فایل سرور، اعلان فوریت‌ها، محدودسازی `/docs`) هنوز باقی‌اند.

---

## پیشنهاد برای فازهای بعدی (فراتر از roadmap فعلی)

روادمپ اولیه کامل شد. چند ایده‌ی طبیعی برای ادامه، اگر خواستید:
- صفحه‌ی داشبورد با آمار کلی (تعداد فایل فعال، قراردادهای رو‌به‌اتمام این هفته) در تب اول
- اتصال ماژول یادآوری به یک API پیامک برای اطلاع‌رسانی خودکار به مشاور
- تست خودکار (`pytest`) برای منطق دسترسی و فیلترها، تا تغییرات آینده این رفتارها را خراب نکنند
- بسته‌بندی نهایی با PyInstaller + Inno Setup و اجرای واقعی فاز ۷ روی یک سیستم ویندوزی واقعی
