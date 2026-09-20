# -*- coding: utf-8 -*-
"""تبدیل عدد به حروف فارسی — بدون وابستگی خارجی.
پشتیبانی تا بیلیارد (۱۰^۱۵) — برای مبالغ ملکی بیش از کافی.
مثال: 2_450_500_000 → «دو میلیارد و چهارصد و پنجاه میلیون و پانصد هزار»"""

ONES = ["", "یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه"]
TEENS = ["ده", "یازده", "دوازده", "سیزده", "چهارده", "پانزده", "شانزده", "هفده", "هجده", "نوزده"]
TENS = ["", "", "بیست", "سی", "چهل", "پنجاه", "شصت", "هفتاد", "هشتاد", "نود"]
HUNDREDS = ["", "صد", "دویست", "سیصد", "چهارصد", "پانصد", "ششصد", "هفتصد", "هشتصد", "نهصد"]
SCALES = ["", " هزار", " میلیون", " میلیارد", " هزار میلیارد", " بیلیارد"]


def _three_digits_to_words(n: int) -> str:
    """۰ تا ۹۹۹"""
    parts = []
    h, rest = divmod(n, 100)
    if h:
        parts.append(HUNDREDS[h])
    if rest >= 10 and rest < 20:
        parts.append(TEENS[rest - 10])
    else:
        t, o = divmod(rest, 10)
        if t:
            parts.append(TENS[t])
        if o:
            parts.append(ONES[o])
    return " و ".join(parts)


def number_to_words(n) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    if n == 0:
        return "صفر"
    if n < 0:
        return "منفی " + number_to_words(-n)

    groups = []
    while n > 0:
        groups.append(n % 1000)
        n //= 1000

    words = []
    for i in range(len(groups) - 1, -1, -1):
        g = groups[i]
        if g == 0:
            continue
        if i == 0:
            words.append(_three_digits_to_words(g))
        else:
            # ۱ هزار / ۲ هزار / ۳ میلیون / ۱۰ میلیارد — اعداد ۱/۲/۳ در مقیاس‌ها خلاصه می‌شوند
            words.append(_three_digits_to_words(g) + SCALES[i])
    return " و ".join(words)


def money_to_words(amount) -> str:
    """«۲٬۴۵۰٬۵۰۰٬۰۰۰ تومان» → «دو میلیارد و چهارصد و پنجاه میلیون و پانصد هزار تومان»"""
    words = number_to_words(amount)
    return f"{words} تومان" if words else ""


# ---------- تست سریع از CMD ----------
if __name__ == "__main__":
    tests = [0, 1, 15, 23, 100, 305, 912, 1000, 2500, 12345,
             123_456_789, 2_450_500_000, 20_000_000_000, 1_234_567_890_123]
    for t in tests:
        print(f"{t:,} → {money_to_words(t)}")