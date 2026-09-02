import io
from datetime import date

import jdatetime
import pandas as pd

from app.models.property import Property, DealType
from app.services.excel_schema import COMMON_COLUMNS, DEAL_SHEETS

BOOL_TRUE_VALUES = {"بله", "yes", "true", "1"}


def _parse_bool(value) -> bool:
    if pd.isna(value):
        return False
    return str(value).strip().lower() in BOOL_TRUE_VALUES


def _parse_int(value):
    if pd.isna(value) or str(value).strip() == "":
        return None
    text = str(value).strip().replace(",", "")
    return int(float(text))  # float() هم اعداد اعشاری اکسل مثل 5200000000.0 را قبول می‌کند


def _parse_jalali_date(value):
    if pd.isna(value) or str(value).strip() == "":
        return None
    text = str(value).strip()
    year, month, day = (int(x) for x in text.split("-"))
    return jdatetime.date(year, month, day).togregorian()


def _parse_common_fields(row: pd.Series) -> dict:
    labels = {label: key for key, label in COMMON_COLUMNS}
    result = {}
    for key, label in COMMON_COLUMNS:
        raw = row.get(label)
        if key in ("has_elevator", "has_parking"):
            result[key] = _parse_bool(raw)
        elif key in ("area_m2",):
            result[key] = float(raw) if not pd.isna(raw) and str(raw).strip() != "" else None
        elif key == "rooms":
            result[key] = int(raw) if not pd.isna(raw) and str(raw).strip() != "" else None
        else:
            result[key] = str(raw).strip() if not pd.isna(raw) and str(raw).strip() != "" else None

    if not result.get("city"):
        raise ValueError("ستون «شهر» خالی است")
    return result


def import_workbook(file_bytes: bytes, owner_agent_id: int) -> tuple[list[Property], list[dict]]:
    """
    خروجی: (لیست آبجکت‌های Property آماده برای ثبت, لیست خطاهای ردیف‌به‌ردیف)
    هر خطا: {"sheet": ..., "row": شماره ردیف در اکسل (شامل هدر), "message": ...}
    """
    try:
        sheets = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None, engine="openpyxl")
    except Exception as e:
        raise ValueError(f"فایل اکسل قابل خواندن نیست: {e}")

    new_properties: list[Property] = []
    errors: list[dict] = []

    for deal_type, config in DEAL_SHEETS.items():
        sheet_name = config["sheet_name"]
        if sheet_name not in sheets:
            continue  # این نوع معامله در فایل موجود نیست، نادیده گرفته می‌شود
        df = sheets[sheet_name]

        for i, row in df.iterrows():
            excel_row_number = i + 2  # ردیف ۱ هدر است، pandas از صفر می‌شمارد
            try:
                common = _parse_common_fields(row)
                details = {}
                contract_end_date = None
                for field in config["fields"]:
                    raw = row.get(field["header"])
                    if field["type"] == "int":
                        value = _parse_int(raw)
                    elif field["type"] == "jalali_date":
                        value = _parse_jalali_date(raw)
                    else:
                        value = raw

                    if field["target"] == "column":
                        contract_end_date = value
                    else:
                        details[field["key"]] = value

                prop = Property(
                    owner_agent_id=owner_agent_id,
                    deal_type=DealType(deal_type),
                    contract_end_date=contract_end_date,
                    details=details,
                    **common,
                )
                new_properties.append(prop)

            except Exception as e:
                errors.append({"sheet": sheet_name, "row": excel_row_number, "message": str(e)})

    return new_properties, errors
