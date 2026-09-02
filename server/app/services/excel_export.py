import io

from openpyxl import Workbook
from openpyxl.styles import Font

DEAL_TYPE_LABELS_FA = {"sale": "فروش", "presale": "پیش‌خرید", "rent": "اجاره", "mortgage": "رهن کامل"}


def build_properties_excel(properties: list[dict]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "فایل‌ها"
    ws.sheet_view.rightToLeft = True

    headers = ["شهر", "منطقه", "آدرس", "متراژ", "اتاق", "نوع معامله", "تاریخ پایان قرارداد", "نام مالک", "تلفن مالک"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for p in properties:
        ws.append([
            p.get("city") or "",
            p.get("district") or "",
            p.get("address") or "",
            p.get("area_m2") or "",
            p.get("rooms") or "",
            DEAL_TYPE_LABELS_FA.get(p.get("deal_type"), p.get("deal_type") or ""),
            p.get("contract_end_date") or "",
            p.get("owner_name") or "",
            p.get("owner_phone") or "",
        ])

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
