@echo off
REM این اسکریپت را روی یک سیستم ویندوزی واقعی، از داخل پوشه‌ی client اجرا کنید
REM (بعد از فعال‌سازی venv و نصب requirements-dev.txt).

echo === مرحله ۱: پاک‌سازی build قبلی ===
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

echo === مرحله ۲: ساخت exe با PyInstaller ===
pyinstaller --noconfirm --clean build_client.spec
if errorlevel 1 (
    echo خطا در ساخت exe. لطفاً پیام بالا را بررسی کنید.
    pause
    exit /b 1
)

echo === exe با موفقیت ساخته شد: dist\RealEstateApp.exe ===

echo === مرحله ۳ (اختیاری): کپی به سرور برای مکانیزم آپدیت خودکار ===
echo اگر می‌خواهید این نسخه از طریق مکانیزم آپدیت خودکار به کلاینت‌های قدیمی‌تر معرفی شود:
echo فایل dist\RealEstateApp.exe را در پوشه‌ی server\static_installers\ کپی کنید
echo و APP_VERSION را در فایل .env سرور به‌روزرسانی کنید.

echo.
echo === مرحله ۴ (اختیاری): ساخت نصب‌کننده‌ی ویندوزی با Inno Setup ===
echo اگر Inno Setup نصب است، این خط را از حالت کامنت خارج کنید یا دستی اجرا کنید:
echo "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" install_script.iss

pause
