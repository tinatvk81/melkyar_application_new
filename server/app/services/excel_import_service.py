import io
from datetime import date

import jdatetime
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.property import Property, DealType, PropertyStatus
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


def _normalize(text) -> str:
    return " ".join(str(text).strip().lower().split()) if text else ""


def _duplicate_signature(city: str, address: str, owner_phone: str) -> tuple | None:
    """
    امضای تشخیص تکراری بودن یک فایل: شهر + آدرس + تلفن مالک (نرمال‌شده، بدون
    حساسیت به فاصله‌ی اضافی یا بزرگی/کوچکی حروف). اگر آدرس و تلفن هردو خالی
    باشند، اطلاعات کافی برای تشخیص تکراری بودن نداریم و بی‌خیال این بررسی
    می‌شویم (بهتر از رد کردن اشتباهیِ یک فایل واقعی).
    """
    norm_address = _normalize(address)
    norm_phone = _normalize(owner_phone)
    if not norm_address and not norm_phone:
        return None
    return (_normalize(city), norm_address, norm_phone)


def _find_existing_duplicate(db: Session, owner_agent_id: int, deal_type: str, signature: tuple):
    city, address, owner_phone = signature
    q = db.query(Property).filter(
        Property.owner_agent_id == owner_agent_id,
        Property.deal_type == DealType(deal_type),
        Property.status == PropertyStatus.active,
        func.lower(Property.city) == city,
    )
    if address:
        q = q.filter(func.lower(func.trim(Property.address)) == address)
    if owner_phone:
        q = q.filter(func.lower(func.trim(Property.owner_phone)) == owner_phone)
    return q.first()


def import_workbook(
    file_bytes: bytes, owner_agent_id: int, db: Session
) -> tuple[list[Property], list[dict], list[dict]]:
    """
    خروجی: (لیست آبجکت‌های Property آماده برای ثبت, لیست خطاهای ردیف‌به‌ردیف, لیست ردیف‌های تکراری نادیده‌گرفته‌شده)
    هر خطا/تکراری: {"sheet": ..., "row": شماره ردیف در اکسل (شامل هدر), "message": ...}

    تشخیص تکراری در دو سطح انجام می‌شود:
    ۱. در برابر فایل‌های از‌قبل‌موجود در دیتابیس (همان مشاور، همان نوع معامله، همان شهر/آدرس/تلفن)
    ۲. در برابر ردیف‌های دیگر همین فایل اکسل (اگر خودِ فایل اکسل تکرار داشته باشد)
    """
    try:
        # نکته‌ی مهم (باگ واقعی که در تست پیدا شد): بدون dtype=str، اگر ستونی
        # مثل «تلفن مالک» فقط شامل مقادیر عددی‌شکل باشد، pandas آن را به‌طور
        # خودکار به نوع عددی تبدیل می‌کند و صفر ابتدایی شماره تلفن‌های ایرانی
        # (مثل 09121112233) را حذف می‌کند — که هم داده را خراب می‌کند و هم
        # باعث می‌شود تشخیص تکراری بر اساس تلفن درست کار نکند.
        sheets = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None, engine="openpyxl", dtype=str)
    except Exception as e:
        raise ValueError(f"فایل اکسل قابل خواندن نیست: {e}")

    new_properties: list[Property] = []
    errors: list[dict] = []
    duplicates: list[dict] = []
    seen_in_this_file: set = set()

    for deal_type, config in DEAL_SHEETS.items():
        sheet_name = config["sheet_name"]
        if sheet_name not in sheets:
            continue  # این نوع معامله در فایل موجود نیست، نادیده گرفته می‌شود
        df = sheets[sheet_name]

        for i, row in df.iterrows():
            excel_row_number = i + 2  # ردیف ۱ هدر است، pandas از صفر می‌شمارد
            try:
                common = _parse_common_fields(row)

                signature = _duplicate_signature(common["city"], common.get("address"), common.get("owner_phone"))
                if signature is not None:
                    if signature in seen_in_this_file:
                        duplicates.append({
                            "sheet": sheet_name, "row": excel_row_number,
                            "message": "این ردیف با ردیف دیگری در همین فایل اکسل تکراری به‌نظر می‌رسد (آدرس/تلفن یکسان)",
                        })
                        continue
                    existing = _find_existing_duplicate(db, owner_agent_id, deal_type, signature)
                    if existing is not None:
                        duplicates.append({
                            "sheet": sheet_name, "row": excel_row_number,
                            "message": f"احتمالاً تکراری است — فایل مشابه از قبل با شناسه‌ی #{existing.id} ثبت شده",
                        })
                        continue
                    seen_in_this_file.add(signature)

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

    return new_properties, errors, duplicates
