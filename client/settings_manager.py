"""
تنظیمات سرور دیگر داخل کد هاردکد نیست. این فایل یک settings.json کنار خودِ
فایل اجرایی (exe) می‌سازد و از آن می‌خواند. یعنی اگر IP سرور دفتر عوض شد،
مدیر دفتر فقط این فایل را با Notepad باز می‌کند و آدرس را عوض می‌کند —
دیگر نیازی به دانستن برنامه‌نویسی یا ساخت دوباره‌ی exe نیست. (همچنین از
داخل خودِ برنامه هم — در پنجره‌ی ورود، دکمه‌ی «تنظیمات اتصال» — قابل تغییر است.)
"""
import json
import os
import sys

from config import SERVER_URL as BUILTIN_DEFAULT_SERVER_URL

SETTINGS_FILENAME = "settings.json"

if getattr(sys, "frozen", False):
    # اجرا از داخل exe ساخته‌شده با PyInstaller — کنار خودِ exe
    _APP_DIR = os.path.dirname(sys.executable)
else:
    # اجرا از سورس پایتون در حال توسعه — کنار main.py
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))

SETTINGS_PATH = os.path.join(_APP_DIR, SETTINGS_FILENAME)

DEFAULTS = {"server_url": BUILTIN_DEFAULT_SERVER_URL}


def load_settings() -> dict:
    if not os.path.exists(SETTINGS_PATH):
        save_settings(DEFAULTS)
        return dict(DEFAULTS)
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULTS)
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError):
        # فایل خراب/ناخوانا شده — به‌جای کرش کردن برنامه، مقدار پیش‌فرض را برگردان
        return dict(DEFAULTS)


def save_settings(data: dict) -> None:
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_server_url() -> str:
    return load_settings().get("server_url") or BUILTIN_DEFAULT_SERVER_URL


def set_server_url(url: str) -> None:
    settings = load_settings()
    settings["server_url"] = url.rstrip("/")
    save_settings(settings)
