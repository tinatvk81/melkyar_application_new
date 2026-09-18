"""PDF دفتر حساب مشاور/مشاوران — هم‌سبک با deal_pdf.py (همان فونت و همان روش فارسی‌سازی)."""
import io
import os

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONT_PATH = os.path.join("app", "resources", "fonts", "Vazirmatn-Regular.ttf")
_font_ok = os.path.exists(FONT_PATH)
if _font_ok:
    pdfmetrics.registerFont(TTFont("Vazir", FONT_PATH))
FONT = "Vazir" if _font_ok else "Helvetica"

STATUS_FA = {"pending": "در جریان", "finalized": "قطعی", "canceled": "لغو شده"}

# ستون‌ها (عنوان، عرض میلی‌متر) — جمع = 180mm = عرض مفید A4 با حاشیه 15mm
_DEAL_COLS = [
    ("#", 9), ("فایل", 12), ("مبلغ معامله (تومان)", 30), ("درصد", 11),
    ("پورسانت (تومان)", 28), ("پرداخت‌شده (تومان)", 27), ("مانده (تومان)", 27),
    ("وضعیت", 16), ("تاریخ قولنامه", 20),
]


def _fa(t):
    return get_display(arabic_reshaper.reshape(str(t)))


def _money(n):
    try:
        return f"{int(n or 0):,}"
    except (TypeError, ValueError):
        return "0"


def _fit(text: str, width_mm: float, size: float) -> str:
    max_w = (width_mm - 2) * mm
    while text and pdfmetrics.stringWidth(text, FONT, size) > max_w:
        text = text[:-2]
    return text


def _page(c, right_x, title: str, subtitle: str) -> float:
    if getattr(c, "_page_started", False):
        c.showPage()
    c._page_started = True
    y = A4[1] - 18 * mm
    c.setFont(FONT, 13)
    c.drawRightString(right_x, y, _fa(title))
    y -= 6.5 * mm
    c.setFont(FONT, 9)
    c.drawRightString(right_x, y, _fa(subtitle))
    y -= 5 * mm
    c.setFont(FONT, 8)
    c.drawRightString(right_x, y, _fa(f"تاریخ چاپ: {__import__('datetime').date.today().isoformat()}"))
    y -= 3 * mm
    c.setLineWidth(0.6)
    c.line(15 * mm, y, right_x, y)
    y -= 6 * mm
    return y


def _summary(c, right_x, y, ledger: dict) -> float:
    c.setFont(FONT, 9.5)
    rows = [
        ("تعداد معامله‌ها", ledger.get("deals_count", 0)),
        ("معامله‌های قطعی", ledger.get("finalized_count", 0)),
        ("کارکرد (پورسانت قطعی)", f"{_money(ledger.get('earned', 0))} تومان"),
        ("خالص پرداخت‌شده", f"{_money(ledger.get('paid_total', 0))} تومان"),
        ("مانده", f"{_money(ledger.get('remaining', 0))} تومان"),
    ]
    for label, value in rows:
        c.drawRightString(right_x, y, _fa(f"{label}: {value}"))
        y -= 5.2 * mm
    return y - 2.5 * mm


def _col_positions(right_x):
    xs, cur = [], right_x
    for _label, w in _DEAL_COLS:
        xs.append(cur)
        cur -= w * mm
    return xs, cur


def _table_header(c, right_x, y) -> float:
    xs, left_x = _col_positions(right_x)
    c.setFont(FONT, 8)
    c.setFillColorRGB(0.94, 0.92, 0.85)
    c.rect(left_x, y - 2 * mm, right_x - left_x, 7 * mm, fill=1, stroke=0)
    c.setFillColorRGB(0, 0, 0)
    for (label, _w), x in zip(_DEAL_COLS, xs):
        c.drawRightString(x - 1.2 * mm, y, _fa(label))
    return y - 9 * mm


def _table_rows(c, right_x, y, deals: list) -> float:
    xs, _left = _col_positions(right_x)
    c.setFont(FONT, 8)
    for d in deals:
        vals = [
            str(d["id"]),
            f"#{d['property_id']}",
            _money(d["deal_amount"]),
            f"{float(d.get('commission_percent') or 0):g}%",
            _money(d["commission_amount"]),
            _money(d.get("paid_total", 0)),
            _money(d.get("remaining", 0)),
            STATUS_FA.get(d.get("status"), str(d.get("status", ""))),
            d.get("contract_date") or "—",
        ]
        for (_label, wmm), x, v in zip(_DEAL_COLS, xs, vals):
            c.drawRightString(x - 1.2 * mm, y, _fit(_fa(v), wmm, 8))
        y -= 5.6 * mm
    return y


def _chunk(items, size):
    size = max(1, size)
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _capacity(y) -> int:
    return max(1, int((y - 22 * mm) / (5.6 * mm)))


def build_agent_ledger_pdf(ledger: dict) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    right = A4[0] - 15 * mm
    title = f"دفتر حساب — {ledger.get('full_name') or ''}"
    c._page_started = False

    y = _page(c, right, title, "حسابداری پورسانت — سامانه ملک‌یار")
    y = _summary(c, right, y, ledger)
    y = _table_header(c, right, y)
    cap = _capacity(y)
    for i, chunk in enumerate(_chunk(ledger.get("deals") or [], cap)):
        if i > 0:
            y = _page(c, right, title, "ادامه‌ی دفتر حساب")
            y = _table_header(c, right, y)
        y = _table_rows(c, right, y, chunk)
    c.save()
    return buf.getvalue()


def build_all_ledgers_pdf(ledgers: list) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    right = A4[0] - 15 * mm
    c._page_started = False
    for L in ledgers:
        title = f"دفتر حساب — {L.get('full_name') or ''}"
        y = _page(c, right, title, "حسابداری پورسانت — گزارش تجمیعی همهٔ کاربران")
        y = _summary(c, right, y, L)
        y = _table_header(c, right, y)
        cap = _capacity(y)
        for i, chunk in enumerate(_chunk(L.get("deals") or [], cap)):
            if i > 0:
                y = _page(c, right, title, "ادامه")
                y = _table_header(c, right, y)
            y = _table_rows(c, right, y, chunk)
    c.save()
    return buf.getvalue()