"""
تولید PDF فارسی نیازمند دو مرحله‌ی اضافه نسبت به انگلیسی است، وگرنه حروف
به‌هم‌چسبیده و در جهت اشتباه چاپ می‌شوند:
  ۱. Reshaping: حروف فارسی بسته به موقعیتشان در کلمه شکل متفاوتی دارند
     (ابتدا/وسط/انتها/تنها) — کتابخانه‌ی arabic_reshaper این را انجام می‌دهد.
  ۲. Bidi: چیدمان راست‌به‌چپ متن — کتابخانه‌ی python-bidi این را انجام می‌دهد.
هر رشته‌ی فارسی که در PDF چاپ می‌شود باید از تابع fa() این فایل رد شود.
"""
import io
import os

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "resources", "fonts", "Vazirmatn-Regular.ttf")
FONT_NAME = "Vazirmatn"

DEAL_TYPE_LABELS_FA = {"sale": "فروش", "presale": "پیش‌خرید", "rent": "اجاره", "mortgage": "رهن کامل"}

_font_registered = False


def _ensure_font_registered() -> str:
    """فونت را یک‌بار در reportlab ثبت می‌کند؛ اگر فایل فونت پیدا نشد، به Helvetica
    برمی‌گردد (که فارسی را پشتیبانی نمی‌کند، ولی برنامه حداقل کرش نمی‌کند)."""
    global _font_registered
    if not _font_registered:
        if os.path.exists(FONT_PATH):
            pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
            _font_registered = True
        else:
            return "Helvetica"
    return FONT_NAME


def fa(text) -> str:
    """آماده‌سازی یک رشته‌ی فارسی برای چاپ صحیح در PDF."""
    if text is None or text == "":
        return ""
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)


def build_properties_pdf(properties: list[dict], title: str = "فهرست فایل‌های ملکی") -> bytes:
    font_name = _ensure_font_registered()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                             leftMargin=1.2 * cm, rightMargin=1.2 * cm)

    title_style = ParagraphStyle(name="fa-title", fontName=font_name, fontSize=16, alignment=1, spaceAfter=14)
    meta_style = ParagraphStyle(name="fa-meta", fontName=font_name, fontSize=9, alignment=1,
                                 textColor=colors.grey, spaceAfter=10)

    elements = [
        Paragraph(fa(title), title_style),
        Paragraph(fa(f"تعداد فایل: {len(properties)}"), meta_style),
        Spacer(1, 6),
    ]

    # ستون‌ها به‌ترتیب معکوس داده می‌شوند تا وقتی جدول چپ‌به‌راست رسم می‌شود،
    # ترتیب دیداری آن برای خواننده‌ی فارسی‌زبان راست‌به‌چپ به‌نظر برسد.
    headers_logical = ["شهر", "منطقه", "نوع معامله", "متراژ", "اتاق", "آدرس", "پایان قرارداد"]
    headers_display = list(reversed([fa(h) for h in headers_logical]))
    data = [headers_display]

    for p in properties:
        row_logical = [
            p.get("city") or "",
            p.get("district") or "",
            DEAL_TYPE_LABELS_FA.get(p.get("deal_type"), p.get("deal_type") or ""),
            str(p.get("area_m2") or ""),
            str(p.get("rooms") or ""),
            p.get("address") or "",
            p.get("contract_end_date") or "",
        ]
        data.append(list(reversed([fa(v) for v in row_logical])))

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
    ]))
    elements.append(table)

    doc.build(elements)
    return buffer.getvalue()


def build_agent_performance_pdf(agents: list[dict]) -> bytes:
    font_name = _ensure_font_registered()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)

    title_style = ParagraphStyle(name="fa-title", fontName=font_name, fontSize=16, alignment=1, spaceAfter=14)
    elements = [Paragraph(fa("گزارش عملکرد مشاوران"), title_style), Spacer(1, 6)]

    headers_logical = ["نام مشاور", "تعداد کل فایل", "۳۰ روز اخیر", "فروش", "پیش‌خرید", "اجاره", "رهن کامل"]
    data = [list(reversed([fa(h) for h in headers_logical]))]

    for agent in agents:
        by_type = agent.get("by_deal_type", {})
        row_logical = [
            agent.get("full_name") or agent.get("username") or "",
            str(agent.get("total", 0)),
            str(agent.get("last_30_days", 0)),
            str(by_type.get("sale", 0)),
            str(by_type.get("presale", 0)),
            str(by_type.get("rent", 0)),
            str(by_type.get("mortgage", 0)),
        ]
        data.append(list(reversed([fa(v) for v in row_logical])))

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
    ]))
    elements.append(table)

    doc.build(elements)
    return buffer.getvalue()
