# -*- coding: utf-8 -*-
"""آپلود نصب‌کنندهٔ ملک‌یار روی هاست — تکه‌تکه، مقاوم به شبکهٔ ضعیف."""
import json
import os
import sys

import requests

HOST = "https://melkyarapp.ir"
ADMIN_USER = "amllak"
ADMIN_PASS = "amllaktavakkoli"
EXE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "RealEstateApp.exe")
CHUNKS = 5


def main():
    if not os.path.exists(EXE_PATH):
        print(f"[خطا] فایل پیدا نشد: {EXE_PATH}")
        print("اول build_installer.bat را اجرا کن.")
        input("Enter برای بستن...")
        sys.exit(1)

    size = os.path.getsize(EXE_PATH)
    print(f"=== آپلود نصب‌کنندهٔ ملک‌یار ===")
    print(f"فایل: {EXE_PATH} ({size:,} بایت)")

    # 1) توکن
    print("[1/5] گرفتن توکن...")
    r = requests.post(f"{HOST}/auth/login",
                      data={"username": ADMIN_USER, "password": ADMIN_PASS}, timeout=15)
    if r.status_code != 200:
        print(f"[خطا] لاگین ناموفق: {r.text}")
        input("Enter برای بستن..."); sys.exit(1)
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2) تقسیم
    print(f"[2/5] تقسیم به {CHUNKS} تکه...")
    with open(EXE_PATH, "rb") as f:
        data = f.read()
    chunk_size = (len(data) + CHUNKS - 1) // CHUNKS
    parts = [data[i * chunk_size:(i + 1) * chunk_size] for i in range(CHUNKS)]
    part_paths = []
    for i, part in enumerate(parts):
        p = os.path.join(os.path.dirname(EXE_PATH), f"part_{i}.bin")
        with open(p, "wb") as pf:
            pf.write(part)
        part_paths.append(p)

    # 3) آپلود تکه‌ها (۳ بار تلاش برای هر تکه)
    print(f"[3/5] آپلود {CHUNKS} تکه...")
    for i, pp in enumerate(part_paths):
        ok = False
        for attempt in range(1, 4):
            try:
                with open(pp, "rb") as pf:
                    r = requests.post(f"{HOST}/installers/chunk", headers=headers,
                                      data={"index": str(i)},
                                      files={"file": (os.path.basename(pp), pf)},
                                      timeout=120)
                if r.status_code == 200 and r.json().get("ok"):
                    print(f"      تکه {i} ✓ ({len(part):,} بایت)")
                    ok = True
                    break
                print(f"      تکه {i} تلاش {attempt}/3 ناموفق: {r.text[:120]}")
            except Exception as e:
                print(f"      تکه {i} تلاش {attempt}/3 خطا: {e}")
            import time; time.sleep(2)
        if not ok:
            print(f"[خطا] تکه {i} هر ۳ بار شکست خورد.")
            input("Enter برای بستن..."); sys.exit(1)

    # 4) finalize
    print("[4/5] چسباندن تکه‌ها...")
    r = requests.post(f"{HOST}/installers/finalize", headers=headers,
                      data={"count": str(CHUNKS)}, timeout=120)
    print("  پاسخ سرور:", r.text[:200])
    if r.status_code != 200 or not r.json().get("ok"):
        print("[خطا] finalize ناموفق.")
        input("Enter برای بستن..."); sys.exit(1)

    # 5) پاک‌سازی
    print("[5/5] پاک‌سازی تکه‌های محلی...")
    for pp in part_paths:
        try: os.remove(pp)
        except OSError: pass

    print()
    print("=== ✅ آپلود کامل شد ===")
    print("تست دانلود:")
    print(f"  {HOST}/static-installers/RealEstateApp-Setup-1.4.0.exe")
    input("Enter برای بستن...")


if __name__ == "__main__":
    main()