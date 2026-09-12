import io
import os
from datetime import date

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONT_PATH = os.path.join("app", "resources", "fonts", "Vazirmatn-Regular.ttf")
if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont("Vazir", FONT_PATH))
FONT = "Vazir" if os.path.exists(FONT_PATH) else "Helvetica"

TEMPLATE_PATH = os.path.join("contract_template.txt")
STATUS_FA = {"pending": "در جریان", "finalized": "قطعی", "canceled": "لغو شده"}


def _fa(t):
    return get_display(arabic_reshaper.reshape(str(t)))


def _wrap(c, text, max_chars=90):
    """متن را خط‌به‌خط می‌شکند تا از صفحه بیرون نزند."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > max_chars:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    return lines


def build_contract_pdf(deal: dict, agent_name: str, payments: list[dict],
                       agency_name: str = "آژانس املاک") -> bytes:
    # --- جای‌گذاری مقادیر در قالب ---
    tpl = open(TEMPLATE_PATH, encoding="utf-8").read() if os.path.exists(TEMPLATE_PATH) \
        else "قرارداد شماره {deal_no} — مبلغ {deal_amount} تومان"

    if deal.get("contract_date"):
        cdate = deal["contract_date"]
        try:
            import jdatetime
            j = jdatetime.date.fromgregorian(date=date.fromisoformat(cdate))
            cdate = j.strftime("%Y/%m/%d")
        except Exception:
            pass
    else:
        cdate = "—"

    rows_txt = "\n"
    if payments:
        rows_txt = "\nریز پرداخت‌ها:\n" + "\n".join(
            f"• {int(p['amount']):,} تومان — {p.get('paid_date') or '—'} — {p.get('note') or ''}"
            for p in payments) + "\n"

    values = {
        "deal_no": str(deal.get("id", "")),
        "property_id": str(deal.get("property_id", "")),
        "deal_amount": f"{int(deal.get('deal_amount', 0)):,}",
        "commission_percent": f"{deal.get('commission_percent', 0):g}",
        "commission_amount": f"{int(deal.get('commission_amount', 0)):,}",
        "paid_total": f"{int(deal.get('paid_total', 0)):,}",
        "remaining": f"{int(deal.get('remaining', 0)):,}",
        "contract_date": cdate,
        "agent_name": agent_name,
        "agency_name": agency_name,
        "payments_table": rows_txt,
        "status": STATUS_FA.get(deal.get("status"), ""),
    }
    content = tpl.format(**values)

    # --- رندر PDF ---
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 60
    c.setFont(FONT, 12)
    for para in content.split("\n"):
        if not para.strip():
            y -= 8
            continue
        for line in _wrap(c, para.strip()):
            if y < 60:
                c.showPage()
                c.setFont(FONT, 12)
                y = h - 60
            c.drawRightString(w - 50, y, _fa(line))
            y -= 20
    c.showPage()
    c.save()
    return buf.getvalue()