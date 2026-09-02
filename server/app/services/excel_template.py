import io

from openpyxl import Workbook
from openpyxl.styles import Font

from app.services.excel_schema import COMMON_COLUMNS, DEAL_SHEETS, GUIDE_TEXT_LINES


def build_template_workbook() -> bytes:
    wb = Workbook()
    wb.remove(wb.active)  # حذف شیت خالی پیش‌فرض

    for deal_type, config in DEAL_SHEETS.items():
        ws = wb.create_sheet(title=config["sheet_name"])
        headers = [label for _, label in COMMON_COLUMNS] + [f["header"] for f in config["fields"]]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        # یک ردیف نمونه برای راهنمایی چشمی
        ws.append([""] * len(headers))

    guide_ws = wb.create_sheet(title="راهنما")
    for i, line in enumerate(GUIDE_TEXT_LINES, start=1):
        guide_ws.cell(row=i, column=1, value=line)
    guide_ws.sheet_view.rightToLeft = True

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
