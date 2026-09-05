"""
فرم افزودن/ویرایش فایل ملکی — فیلدهای مشترک همیشه نمایش داده می‌شوند،
فیلدهای اختصاصی بر اساس نوع معامله (فروش/پیش‌خرید/اجاره/رهن‌کامل) عوض می‌شوند.
"""
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QVBoxLayout, QLineEdit, QComboBox, QDoubleSpinBox,
    QSpinBox, QCheckBox, QTextEdit, QPushButton, QHBoxLayout, QWidget,
    QMessageBox, QLabel
)

from api_client import api_client, ApiError
from session import handle_api_error
from ui.jalali_date_edit import JalaliDateEdit
from ui.property_gallery_dialog import PropertyGalleryDialog

DEAL_TYPE_LABELS = {
    "sale": "فروش",
    "presale": "پیش‌خرید",
    "rent": "اجاره",
    "mortgage": "رهن کامل",
}


class MoneyLineEdit(QLineEdit):
    """فیلد ورودی مبلغ — فقط رقم می‌پذیرد، چون مبالغ ملکی می‌تواند از سقف int عادی هم بزرگ‌تر باشد."""

    def __init__(self):
        super().__init__()
        self.setPlaceholderText("مثلاً 5200000000")
        self.setAlignment(Qt.AlignRight)

    def value(self):
        text = self.text().strip().replace(",", "")
        if not text:
            return None
        if not text.isdigit():
            raise ValueError("مبلغ باید فقط عدد باشد")
        return int(text)

    def set_value(self, v):
        self.setText(str(int(v)) if v is not None else "")


class PropertyFormDialog(QDialog):
    """
    property: دیکشنری فایل موجود برای ویرایش (خروجی PropertyRead)، یا None برای ثبت فایل جدید.
    on_saved: تابعی که بعد از ذخیره‌ی موفق صدا زده می‌شود (برای رفرش فهرست).
    """

    def __init__(self, property_data: dict | None, on_saved):
        super().__init__()
        self.property_data = property_data
        self.on_saved = on_saved
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("ویرایش فایل" if property_data else "افزودن فایل جدید")
        self.resize(480, 620)

        self._build_ui()
        if property_data:
            self._fill_from_existing()
        else:
            self._on_deal_type_changed(self.deal_type_combo.currentData())

    # ---------------------------------------------------------------- UI
    def _build_ui(self):
        outer = QVBoxLayout()

        common_form = QFormLayout()
        self.deal_type_combo = QComboBox()
        for value, label in DEAL_TYPE_LABELS.items():
            self.deal_type_combo.addItem(label, value)
        self.deal_type_combo.currentIndexChanged.connect(
            lambda _i: self._on_deal_type_changed(self.deal_type_combo.currentData())
        )
        common_form.addRow("نوع معامله:", self.deal_type_combo)

        self.city_input = QLineEdit()
        common_form.addRow("شهر:", self.city_input)
        self.district_input = QLineEdit()
        common_form.addRow("منطقه/محله:", self.district_input)
        self.address_input = QLineEdit()
        common_form.addRow("آدرس:", self.address_input)

        self.area_input = QDoubleSpinBox()
        self.area_input.setRange(0, 100000)
        self.area_input.setSuffix(" متر مربع")
        common_form.addRow("متراژ:", self.area_input)

        self.rooms_input = QSpinBox()
        self.rooms_input.setRange(0, 20)
        common_form.addRow("تعداد اتاق:", self.rooms_input)

        checks_row = QHBoxLayout()
        self.elevator_check = QCheckBox("آسانسور")
        self.parking_check = QCheckBox("پارکینگ")
        checks_row.addWidget(self.elevator_check)
        checks_row.addWidget(self.parking_check)
        checks_widget = QWidget()
        checks_widget.setLayout(checks_row)
        common_form.addRow("امکانات:", checks_widget)

        self.owner_name_input = QLineEdit()
        common_form.addRow("نام مالک:", self.owner_name_input)
        self.owner_phone_input = QLineEdit()
        common_form.addRow("تلفن مالک:", self.owner_phone_input)

        outer.addLayout(common_form)

        # --- بخش اختصاصی نوع معامله ---
        outer.addWidget(QLabel("جزئیات معامله:"))
        self.details_form = QFormLayout()
        details_widget = QWidget()
        details_widget.setLayout(self.details_form)
        outer.addWidget(details_widget)

        # فیلدهای اختصاصی (همه ساخته می‌شوند، فقط بر اساس نوع نمایش/مخفی می‌شوند)
        self.price_input = MoneyLineEdit()                 # فروش
        self.total_price_input = MoneyLineEdit()            # پیش‌خرید
        self.delivery_date_input = JalaliDateEdit(allow_empty=True)  # پیش‌خرید
        self.monthly_rent_input = MoneyLineEdit()             # اجاره
        self.deposit_input = MoneyLineEdit()                   # اجاره (ودیعه)
        self.deposit_full_input = MoneyLineEdit()                # رهن‌کامل

        # --- تاریخ پایان قرارداد (فقط اجاره/رهن) ---
        self.contract_end_row_label = QLabel("تاریخ پایان قرارداد:")
        self.contract_end_input = JalaliDateEdit(allow_empty=True)

        self.notes_input = QTextEdit()
        self.notes_input.setFixedHeight(80)
        outer.addWidget(QLabel("توضیحات:"))
        outer.addWidget(self.notes_input)

        save_btn = QPushButton("ذخیره")
        save_btn.clicked.connect(self.handle_save)
        cancel_btn = QPushButton("انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_row = QHBoxLayout()

        if self.property_data:
            # گالری فقط برای فایل‌های از قبل ذخیره‌شده در دسترس است، چون آپلود عکس
            # به property_id نیاز دارد که برای فایل جدید هنوز وجود ندارد.
            gallery_btn = QPushButton("گالری تصاویر")
            gallery_btn.clicked.connect(self.handle_open_gallery)
            btn_row.addWidget(gallery_btn)

        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        outer.addLayout(btn_row)

        self.setLayout(outer)

    def _clear_details_form(self):
        while self.details_form.rowCount():
            self.details_form.removeRow(0)

    def _on_deal_type_changed(self, deal_type: str):
        self._clear_details_form()

        if deal_type == "sale":
            self.details_form.addRow("قیمت (تومان):", self.price_input)

        elif deal_type == "presale":
            self.details_form.addRow("مبلغ کل (تومان):", self.total_price_input)
            self.details_form.addRow("تاریخ تحویل:", self.delivery_date_input)

        elif deal_type == "rent":
            self.details_form.addRow("ودیعه (تومان):", self.deposit_input)
            self.details_form.addRow("اجاره‌ی ماهانه (تومان):", self.monthly_rent_input)
            self.details_form.addRow(self.contract_end_row_label, self.contract_end_input)

        elif deal_type == "mortgage":
            self.details_form.addRow("مبلغ رهن کامل (تومان):", self.deposit_full_input)
            self.details_form.addRow(self.contract_end_row_label, self.contract_end_input)

    # ---------------------------------------------------------- Fill / Save
    def _fill_from_existing(self):
        p = self.property_data
        idx = self.deal_type_combo.findData(p["deal_type"])
        if idx >= 0:
            self.deal_type_combo.setCurrentIndex(idx)  # این خودش _on_deal_type_changed را صدا می‌زند

        self.city_input.setText(p.get("city") or "")
        self.district_input.setText(p.get("district") or "")
        self.address_input.setText(p.get("address") or "")
        self.area_input.setValue(p.get("area_m2") or 0)
        self.rooms_input.setValue(p.get("rooms") or 0)
        self.elevator_check.setChecked(bool(p.get("has_elevator")))
        self.parking_check.setChecked(bool(p.get("has_parking")))
        self.owner_name_input.setText(p.get("owner_name") or "")
        self.owner_phone_input.setText(p.get("owner_phone") or "")
        self.notes_input.setPlainText(p.get("notes") or "")

        details = p.get("details") or {}
        if p["deal_type"] == "sale":
            self.price_input.set_value(details.get("price"))
        elif p["deal_type"] == "presale":
            self.total_price_input.set_value(details.get("total_price"))
            if details.get("delivery_date"):
                self.delivery_date_input.set_gregorian_date(date.fromisoformat(details["delivery_date"]))
        elif p["deal_type"] == "rent":
            self.deposit_input.set_value(details.get("deposit"))
            self.monthly_rent_input.set_value(details.get("monthly_rent"))
        elif p["deal_type"] == "mortgage":
            self.deposit_full_input.set_value(details.get("deposit_full"))

        if p.get("contract_end_date"):
            self.contract_end_input.set_gregorian_date(date.fromisoformat(p["contract_end_date"]))

    def _collect_payload(self) -> dict:
        deal_type = self.deal_type_combo.currentData()
        details = {}
        contract_end_date = None

        try:
            if deal_type == "sale":
                details["price"] = self.price_input.value()
            elif deal_type == "presale":
                details["total_price"] = self.total_price_input.value()
                details["delivery_date"] = self.delivery_date_input.get_iso_string()
            elif deal_type == "rent":
                details["deposit"] = self.deposit_input.value()
                details["monthly_rent"] = self.monthly_rent_input.value()
                contract_end_date = self.contract_end_input.get_iso_string()
            elif deal_type == "mortgage":
                details["deposit_full"] = self.deposit_full_input.value()
                contract_end_date = self.contract_end_input.get_iso_string()
        except ValueError as e:
            raise ValueError(str(e))

        return {
            "deal_type": deal_type,
            "city": self.city_input.text().strip(),
            "district": self.district_input.text().strip() or None,
            "address": self.address_input.text().strip() or None,
            "area_m2": self.area_input.value() or None,
            "rooms": self.rooms_input.value() or None,
            "has_elevator": self.elevator_check.isChecked(),
            "has_parking": self.parking_check.isChecked(),
            "owner_name": self.owner_name_input.text().strip() or None,
            "owner_phone": self.owner_phone_input.text().strip() or None,
            "contract_end_date": contract_end_date,
            "details": details,
            "notes": self.notes_input.toPlainText().strip() or None,
        }

    def handle_open_gallery(self):
        label = self.property_data.get("address") or self.property_data.get("city") or ""
        dialog = PropertyGalleryDialog(self.property_data["id"], property_label=label)
        dialog.exec()

    def handle_save(self):
        if not self.city_input.text().strip():
            QMessageBox.warning(self, "خطا", "وارد کردن شهر الزامی است.")
            return

        try:
            payload = self._collect_payload()
        except ValueError as e:
            QMessageBox.warning(self, "خطا در مقدار عددی", str(e))
            return

        try:
            if self.property_data:
                payload["version"] = self.property_data["version"]
                api_client.update_property(self.property_data["id"], payload)
            else:
                api_client.create_property(payload)
        except ApiError as e:
            if e.status_code == 409:
                # قفل هم‌زمان: شخص دیگری بین‌این‌حین این فایل را تغییر داده است.
                # به‌جای رونویسی بی‌صدا، به کاربر اطلاع می‌دهیم که باید فایل را
                # دوباره باز کند (این دیالوگ بسته می‌شود تا فهرست دوباره تازه شود).
                QMessageBox.warning(
                    self, "تغییر هم‌زمان",
                    "این فایل توسط شخص دیگری تغییر کرده است.\n"
                    "برای جلوگیری از رونویسی تغییرات او، لطفاً این پنجره را ببندید "
                    "و فایل را دوباره باز کنید تا آخرین نسخه را ببینید.",
                )
                self.on_saved()  # فهرست پشت این پنجره را تازه کن تا نسخه‌ی جدید در دسترس باشد
                self.reject()
                return
            handle_api_error(self, e, "خطا در ذخیره‌سازی", critical=True)
            return

        QMessageBox.information(self, "موفق", "فایل با موفقیت ذخیره شد.")
        self.on_saved()
        self.accept()
