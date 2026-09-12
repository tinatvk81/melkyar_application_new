"""
فرم افزودن/ویرایش فایل ملکی — فیلدهای مشترک همیشه نمایش داده می‌شوند،
فیلدهای اختصاصی بر اساس نوع معامله (فروش/پیش‌خرید/اجاره/رهن‌کامل) عوض می‌شوند.
"""
from datetime import date

from PySide6.QtCore import Qt

from ui.widgets import (PersianSpinBox, PersianDoubleSpinBox, MoneyLineEdit,
                        PhoneLineEdit, TagInputWidget)
from api_client import api_client, ApiError
from session import handle_api_error
from ui.jalali_date_edit import JalaliDateEdit
from ui.property_gallery_dialog import PropertyGalleryDialog
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QVBoxLayout, QLineEdit, QComboBox, QDoubleSpinBox,
    QSpinBox, QCheckBox, QTextEdit, QPushButton, QHBoxLayout, QWidget,
    QMessageBox, QLabel, QScrollArea, QFrame
)
DEAL_TYPE_LABELS = {
    "sale": "فروش",
    "presale": "پیش‌خرید",
    "rent": "اجاره",
    "mortgage": "رهن کامل",
}




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

        self.area_input = PersianDoubleSpinBox(suffix=" متر مربع")
        self.area_input.setRange(0, 100000) 
        common_form.addRow("متراژ:", self.area_input)

        self.rooms_input = PersianSpinBox(minimum=0, maximum=50)
        common_form.addRow("تعداد اتاق:", self.rooms_input)

        checks_row = QHBoxLayout()
        self.elevator_check = QCheckBox("آسانسور")
        self.parking_check = QCheckBox("پارکینگ")
        checks_row.addWidget(self.elevator_check)
        checks_row.addWidget(self.parking_check)
        checks_widget = QWidget()
        checks_widget.setLayout(checks_row)
        common_form.addRow("امکانات:", checks_widget)

        self.extra_amenities = TagInputWidget()
        common_form.addRow("امکانات دلخواه:", self.extra_amenities)

        self.owner_name_input = QLineEdit()
        common_form.addRow("نام مالک:", self.owner_name_input)
        self.owner_phone_input = PhoneLineEdit()
        common_form.addRow("تلفن مالک:", self.owner_phone_input)

        outer.addLayout(common_form)

        # --- بخش اختصاصی نوع معامله ---
        outer.addWidget(QLabel("جزئیات معامله:"))
        self.details_form = QFormLayout()
        details_widget = QWidget()
        details_widget.setLayout(self.details_form)
        outer.addWidget(details_widget)

        # فیلدهای اختصاصی (همه ساخته می‌شوند، فقط بر اساس نوع نمایش/مخفی می‌شوند)
        self.price_input = MoneyLineEdit()     
        self.price_per_m2_label = QLabel("—")
        self.price_input.textChanged.connect(self._update_price_per_m2)
        self.area_input.valueChanged.connect(self._update_price_per_m2)            # فروش
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
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self.handle_save)
        cancel_btn = QPushButton("انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_row = QHBoxLayout()

        gallery_btn = QPushButton("گالری تصاویر")
        gallery_btn.clicked.connect(self.handle_open_gallery)
        btn_row.addWidget(gallery_btn)

        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        outer.addLayout(btn_row)

        content = QWidget()
        content.setLayout(outer)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(content)
        base = QVBoxLayout()
        base.addWidget(scroll)
        self.setLayout(base)
        self.setSizeGripEnabled(True)   # دستگیرهٔ تغییر اندازه در گوشه
        self.setMinimumSize(430, 540)
        self.resize(540, 700)

    def _clear_details_form(self):
        while self.details_form.rowCount():
            self.details_form.removeRow(0)

    def _on_deal_type_changed(self, deal_type: str):
        self._clear_details_form()

        if deal_type == "sale":
            self.details_form.addRow("قیمت (تومان):", self.price_input)
            self.details_form.addRow("قیمت هر متر:", self.price_per_m2_label)

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


    def _update_price_per_m2(self):
        if self.deal_type_combo.currentData() != "sale":
            return
        try:
            price = self.price_input.value()
        except ValueError:
            price = None
        area = self.area_input.value()
        if price and area:
            self.price_per_m2_label.setText(f"{round(price / area):,} تومان")
        else:
            self.price_per_m2_label.setText("—")

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
        self.extra_amenities.set_tags(p.get("amenities") or [])
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
            "owner_phone": self.owner_phone_input.normalized_text() or None,
            "amenities": self.extra_amenities.get_tags(),
            "contract_end_date": contract_end_date,
            "details": details,
            "notes": self.notes_input.toPlainText().strip() or None,
        }

    def handle_open_gallery(self):
        if not self.property_data:
            QMessageBox.information(
                self, "گالری تصاویر",
                "برای افزودن عکس، ابتدا باید فایل ذخیره شود (عکس به شناسه‌ی فایل وصل می‌شود).\n"
                "دکمه‌ی «ذخیره» را بزنید — بلافاصله پس از ذخیره، پنجره‌ی گالری باز می‌شود.")
            return
        label = self.property_data.get("address") or self.property_data.get("city") or ""
        PropertyGalleryDialog(self.property_data["id"], property_label=label).exec()

    def handle_save(self):
        if not self.city_input.text().strip():
            QMessageBox.warning(self, "خطا", "وارد کردن شهر الزامی است.")
            return

        if self.owner_phone_input.text().strip() and not self.owner_phone_input.is_valid():
            QMessageBox.warning(self, "خطا", "شماره تلفن معتبر نیست (فقط رقم، ۱۰ یا ۱۱ رقم).")
            return

        try:
            payload = self._collect_payload()
        except ValueError as e:
            QMessageBox.warning(self, "خطا در مقدار عددی", str(e))
            return


        # --- هشدار فایل مشابه/تکراری (مسدودکننده نیست؛ تصمیم با کاربر است) ---
        try:
            matches = api_client.check_duplicate(
                owner_phone=self.owner_phone_input.normalized_text() or None,
                city=self.city_input.text().strip() or None,
                address=self.address_input.text().strip() or None,
            )
        except ApiError:
            matches = []
        if self.property_data:  # در ویرایش، خودِ فایل نباید «مشابه» حساب شود
            matches = [m for m in matches if m["id"] != self.property_data["id"]]
        if matches:
            lines = []
            for m in matches[:5]:
                kind = "تکراری (همان شهر و آدرس)" if m["match_kind"] == "exact" else "همان تلفن مالک"
                lines.append(
                    f"• #{m['id']} — {m['city']} — {m.get('address') or '—'} — "
                    f"{m.get('owner_name') or '—'} / {m.get('owner_phone') or '—'} "
                    f"[ثبت: {m['agent_name']}] ({kind})"
                )
            msg = ("فایل‌های مشابه در سیستم موجود است:\n\n" + "\n".join(lines) +
                   "\n\nبا این حال فایل جدید ثبت شود؟")
            if QMessageBox.question(self, "هشدار فایل مشابه", msg) != QMessageBox.Yes:
                return

        created = None
        try:
            if self.property_data:
                payload["version"] = self.property_data["version"]
                api_client.update_property(self.property_data["id"], payload)
            else:
                created = api_client.create_property(payload)  # پاسخ شامل id فایل تازه است
        except ApiError as e:
            if e.status_code == 409:
                QMessageBox.warning(
                    self, "تغییر هم‌زمان",
                    "این فایل توسط شخص دیگری تغییر کرده است.\n"
                    "برای جلوگیری از رونویسی تغییرات او، لطفاً این پنجره را ببندید "
                    "و فایل را دوباره باز کنید تا آخرین نسخه را ببینید.",
                )
                self.on_saved()
                self.reject()
                return
            handle_api_error(self, e, "خطا در ذخیره‌سازی", critical=True)
            return

        QMessageBox.information(self, "موفق", "فایل با موفقیت ذخیره شد.")
        self.on_saved()

        if created:
            answer = QMessageBox.question(
                self, "افزودن عکس",
                "آیا می‌خواهید همین حالا برای این فایل عکس اضافه کنید؟",
            )
            if answer == QMessageBox.Yes:
                label = created.get("address") or created.get("city") or ""
                PropertyGalleryDialog(created["id"], property_label=label).exec()

        self.accept()