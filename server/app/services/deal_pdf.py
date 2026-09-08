import io
import os

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONT_PATH = os.path.join("app", "resources", "fonts", "Vazirmatn-Regular.ttf")
_font_ok = os.path.exists(FONT_PATH)
if _font_ok:
    pdfmetrics.registerFont(TTFont("Vazir", FONT_PATH))
FONT = "Vazir" if _font_ok else "Helvetica"

STATUS_FA = {"pending": "در جریان", "finalized": "قطعی", "canceled": "لغو شده"}


def _fa(t):
    return get_display(arabic_reshaper.reshape(str(t)))


def _money(n):
    return f"{int(n):,}"


def build_deal_settlement_pdf(deal: dict, agent_name: str, payments: list[dict]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 60
    c.setFont(FONT, 14)
    c.drawCentredString(w / 2, y, _fa("صورتحساب پورسانت معامله"))
    y -= 30
    c.setFont(FONT, 11)
    for line in [
        f"مشاور: {agent_name}",
        f"شماره معامله: {deal['id']} — شماره فایل ملکی: {deal['property_id']}",
        f"مبلغ معامله: {_money(deal['deal_amount'])} تومان",
        f"درصد پورسانت: {deal['commission_percent']}٪ — پورسانت: {_money(deal['commission_amount'])} تومان",
        f"وضعیت: {STATUS_FA.get(deal['status'], str(deal['status']))}",
        "— پرداخت‌ها —",
    ]:
        c.drawRightString(w - 50, y, _fa(line))
        y -= 18
    total = 0
    for p in payments:
        total += int(p["amount"])
        c.setFont(FONT, 10)
        c.drawRightString(w - 60, y, _fa(
            f"• {_money(p['amount'])} تومان | {p.get('paid_date') or '—'} | {p.get('note') or ''}"))
        y -= 16
    y -= 12
    c.setFont(FONT, 12)
    c.drawRightString(w - 50, y, _fa(f"جمع پرداخت‌شده: {_money(total)} تومان")); y -= 20
    c.drawRightString(w - 50, y, _fa(f"مانده: {_money(max(int(deal['commission_amount']) - total, 0))} تومان"))
    c.showPage()
    c.save()
    return buf.getvalue()


def build_balances_pdf(rows: list[dict]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 60
    c.setFont(FONT, 14)
    c.drawCentredString(w / 2, y, _fa("مانده پورسانت مشاوران"))
    y -= 30
    c.setFont(FONT, 11)
    for r in rows:
        c.drawRightString(w - 50, y, _fa(
            f"{r['full_name']}: کارکرد {_money(r['earned'])} — پرداخت‌شده {_money(r['paid'])} — مانده {_money(r['remaining'])} تومان"))
        y -= 20
    c.showPage()
    c.save()
    return buf.getvalue()