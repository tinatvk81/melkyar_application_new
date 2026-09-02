from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox,
    QPushButton, QLabel, QMessageBox
)

from ui.property_form import DEAL_TYPE_LABELS, MoneyLineEdit

TRI_STATE_OPTIONS = [("", "فرقی نمی‌کند"), ("yes", "بله"), ("no", "خیر")]


class PropertyFilterPanel(QWidget):
    """
    پنل فیلتر پیشرفته‌ی فهرست فایل‌ها. هیچ درخواستی خودش نمی‌فرستد — فقط یک
    دیکشنری فیلتر آماده برای پاس دادن به api_client.list_properties(**filters)
    (و همچنین export_properties_pdf/excel، تا خروجی همیشه با همان فیلتر فعلی باشد) می‌سازد.
    """

    def __init__(self, on_apply, on_clear):
        super().__init__()
        self.on_apply = on_apply
        self.on_clear = on_clear
        self.setLayoutDirection(Qt.RightToLeft)

        self.city_input = QLineEdit()
        self.district_input = QLineEdit()

        self.deal_type_combo = QComboBox()
        self.deal_type_combo.addItem("همه", "")
        for value, label in DEAL_TYPE_LABELS.items():
            self.deal_type_combo.addItem(label, value)

        self.min_area_input = QDoubleSpinBox()
        self.min_area_input.setRange(0, 100000)
        self.min_area_input.setSpecialValueText(" ")  # نمایش خالی وقتی مقدار صفر است
        self.max_area_input = QDoubleSpinBox()
        self.max_area_input.setRange(0, 100000)
        self.max_area_input.setSpecialValueText(" ")

        self.min_rooms_input = QSpinBox()
        self.min_rooms_input.setRange(0, 20)
        self.min_rooms_input.setSpecialValueText(" ")

        self.elevator_combo = QComboBox()
        for value, label in TRI_STATE_OPTIONS:
            self.elevator_combo.addItem(label, value)

        self.parking_combo = QComboBox()
        for value, label in TRI_STATE_OPTIONS:
            self.parking_combo.addItem(label, value)

        self.min_price_input = MoneyLineEdit()
        self.min_price_input.setPlaceholderText("حداقل مبلغ (تومان)")
        self.max_price_input = MoneyLineEdit()
        self.max_price_input.setPlaceholderText("حداکثر مبلغ (تومان)")

        apply_btn = QPushButton("اعمال فیلتر")
        apply_btn.clicked.connect(self._handle_apply)
        clear_btn = QPushButton("پاک کردن فیلتر")
        clear_btn.clicked.connect(self._handle_clear)

        grid = QGridLayout()
        grid.addWidget(QLabel("شهر:"), 0, 0)
        grid.addWidget(self.city_input, 0, 1)
        grid.addWidget(QLabel("منطقه:"), 0, 2)
        grid.addWidget(self.district_input, 0, 3)
        grid.addWidget(QLabel("نوع معامله:"), 0, 4)
        grid.addWidget(self.deal_type_combo, 0, 5)

        grid.addWidget(QLabel("متراژ از:"), 1, 0)
        grid.addWidget(self.min_area_input, 1, 1)
        grid.addWidget(QLabel("تا:"), 1, 2)
        grid.addWidget(self.max_area_input, 1, 3)
        grid.addWidget(QLabel("حداقل اتاق:"), 1, 4)
        grid.addWidget(self.min_rooms_input, 1, 5)

        grid.addWidget(QLabel("آسانسور:"), 2, 0)
        grid.addWidget(self.elevator_combo, 2, 1)
        grid.addWidget(QLabel("پارکینگ:"), 2, 2)
        grid.addWidget(self.parking_combo, 2, 3)

        grid.addWidget(QLabel("قیمت از:"), 3, 0)
        grid.addWidget(self.min_price_input, 3, 1)
        grid.addWidget(QLabel("تا:"), 3, 2)
        grid.addWidget(self.max_price_input, 3, 3)
        grid.addWidget(apply_btn, 3, 4)
        grid.addWidget(clear_btn, 3, 5)

        self.setLayout(grid)

    def _handle_apply(self):
        try:
            filters = self.get_filters()
        except ValueError as e:
            QMessageBox.warning(self, "خطا در فیلتر قیمت", str(e))
            return
        self.on_apply(filters)

    def _handle_clear(self):
        self.city_input.clear()
        self.district_input.clear()
        self.deal_type_combo.setCurrentIndex(0)
        self.min_area_input.setValue(0)
        self.max_area_input.setValue(0)
        self.min_rooms_input.setValue(0)
        self.elevator_combo.setCurrentIndex(0)
        self.parking_combo.setCurrentIndex(0)
        self.min_price_input.clear()
        self.max_price_input.clear()
        self.on_clear()

    def get_filters(self) -> dict:
        """فقط فیلترهایی که واقعاً مقدار دارند را برمی‌گرداند (بقیه اصلاً ارسال نمی‌شوند)."""
        filters = {}

        if self.city_input.text().strip():
            filters["city"] = self.city_input.text().strip()
        if self.district_input.text().strip():
            filters["district"] = self.district_input.text().strip()
        if self.deal_type_combo.currentData():
            filters["deal_type"] = self.deal_type_combo.currentData()
        if self.min_area_input.value() > 0:
            filters["min_area"] = self.min_area_input.value()
        if self.max_area_input.value() > 0:
            filters["max_area"] = self.max_area_input.value()
        if self.min_rooms_input.value() > 0:
            filters["min_rooms"] = self.min_rooms_input.value()
        if self.elevator_combo.currentData():
            filters["has_elevator"] = self.elevator_combo.currentData() == "yes"
        if self.parking_combo.currentData():
            filters["has_parking"] = self.parking_combo.currentData() == "yes"

        min_price = self.min_price_input.value()  # ممکن است ValueError بدهد اگر عدد نامعتبر باشد
        if min_price is not None:
            filters["min_price"] = min_price
        max_price = self.max_price_input.value()
        if max_price is not None:
            filters["max_price"] = max_price

        return filters
