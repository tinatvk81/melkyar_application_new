"""ویجت‌های انتخاب استان/شهر و منطقه/محله — با پیش‌فرض خراسان‌رضوی/مشهد و سایر دستی."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QComboBox, QLineEdit, QLabel, QWidget,
)

from ui.geo_data import PROVINCE_CITIES, MASHHAD_DISTRICTS, OTHER, DEFAULT_PROVINCE, DEFAULT_CITY


class GeoCitySelector(QWidget):
    """انتخاب استان و شهر — کمبو + گزینهٔ «سایر...» برای شهر دستی."""

    def __init__(self, province=None, city=None, parent=None):
        super().__init__(parent)
        self._other_city_mode = False
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self.province_combo = QComboBox()
        self.province_combo.addItems(PROVINCE_CITIES.keys())
        self.city_combo = QComboBox()
        self.city_other_input = QLineEdit()
        self.city_other_input.setVisible(False)
        self.city_other_input.setPlaceholderText("نام شهر را دقیق بنویسید…")

        self.province_combo.currentTextChanged.connect(self._fill_cities)
        self.city_combo.currentTextChanged.connect(self._on_city_changed)
        self.city_other_input.editingFinished.connect(self._on_other_city_typed)

        lay.addWidget(QLabel("استان:"))
        lay.addWidget(self.province_combo, 1)
        lay.addWidget(QLabel("شهر:"))
        lay.addWidget(self.city_combo, 1)
        lay.addWidget(self.city_other_input, 1)

        self.province_combo.setCurrentText(province or DEFAULT_PROVINCE)
        self._fill_cities(self.province_combo.currentText())
        self.set_city(city or DEFAULT_CITY)

    def _fill_cities(self, province):
        self.city_combo.blockSignals(True)
        self.city_combo.clear()
        self.city_combo.addItem(OTHER)
        for c in PROVINCE_CITIES.get(province, []):
            self.city_combo.addItem(c)
        self.city_combo.setCurrentText(DEFAULT_CITY if province == DEFAULT_PROVINCE else "")
        self.city_combo.blockSignals(False)
        self._on_city_changed(self.city_combo.currentText())

    def _on_city_changed(self, city):
        if city == OTHER:
            self._other_city_mode = True
            self.city_other_input.setVisible(True)
            self.city_other_input.setFocus()
        else:
            self._other_city_mode = False
            self.city_other_input.setVisible(False)
            self.city_other_input.clear()

    def _on_other_city_typed(self):
        pass  # مقدار در get_city خوانده می‌شود

    def get_city(self) -> str:
        """شهر نهایی: یا از کمبو یا از input «سایر»."""
        if self._other_city_mode:
            return self.city_other_input.text().strip()
        return self.city_combo.currentText().strip() or ""

    def get_province(self) -> str:
        return self.province_combo.currentText().strip() or ""

    def set_city(self, city: str):
        city = (city or "").strip()
        if not city:
            return
        if self.city_combo.findText(city) >= 0:
            self.city_combo.setCurrentText(city)
            self.city_other_input.setVisible(False)
        else:
            self.city_combo.setCurrentText(OTHER)
            self._other_city_mode = True
            self.city_other_input.setVisible(True)
            self.city_other_input.setText(city)


class GeoDistrictSelector(QWidget):
    """منطقهٔ مشهد (۱..۱۳ + سایر) → محله‌های همان منطقه + سایر دستی.
    اگر شهر مشهد نباشد، فقط یک input متنی معمولی نشان می‌دهد."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mashhad_mode = True
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        self._row1 = QHBoxLayout()
        self.district_combo = QComboBox()
        self.district_combo.addItem(OTHER)
        for d in MASHHAD_DISTRICTS.keys():
            self.district_combo.addItem(d)
        self.district_combo.currentTextChanged.connect(self._fill_neighborhoods)

        self.hood_combo = QComboBox()
        self.hood_other_input = QLineEdit()
        self.hood_other_input.setVisible(False)
        self.hood_other_input.setPlaceholderText("نام محله را دقیق بنویسید…")

        self.plain_input = QLineEdit()   # برای شهرهای غیر مشهد
        self.plain_input.setPlaceholderText("منطقه / محله (تایپ آزاد)…")
        self.plain_input.setVisible(False)

        self._row1.addWidget(QLabel("منطقه:"))
        self._row1.addWidget(self.district_combo, 1)
        self._row1.addWidget(QLabel("محله:"))
        self._row1.addWidget(self.hood_combo, 2)
        self._row1.addWidget(self.hood_other_input, 2)
        self._row1.addWidget(self.plain_input, 1)
        lay.addLayout(self._row1)

        self._fill_neighborhoods(self.district_combo.currentText())

    def set_for_city(self, city: str):
        """اگر شهر مشهد است، مناطق/محله‌ها را نشان بده؛ وگرنه input آزاد."""
        self._mashhad_mode = (city.strip() == "مشهد")
        self.district_combo.setVisible(self._mashhad_mode)
        self.hood_combo.setVisible(self._mashhad_mode)
        self.hood_other_input.setVisible(self._mashhad_mode)
        self.plain_input.setVisible(not self._mashhad_mode)

    def _fill_neighborhoods(self, district):
        self.hood_combo.blockSignals(True)
        self.hood_combo.clear()
        self.hood_combo.addItem(OTHER)
        for h in MASHHAD_DISTRICTS.get(district, []):
            self.hood_combo.addItem(h)
        self.hood_combo.blockSignals(False)
        self.hood_other_input.setVisible(self.hood_combo.currentText() == OTHER)

    def get_district(self) -> str:
        if not self._mashhad_mode:
            return ""
        d = self.district_combo.currentText().strip()
        return "" if d == OTHER else d

    def get_value(self) -> str:
        """مقدار نهایی «منطقه/محله» که در فیلد district ذخیره می‌شود."""
        if not self._mashhad_mode:
            return self.plain_input.text().strip()
        h = self.hood_combo.currentText().strip()
        if h == OTHER:
            h = self.hood_other_input.text().strip()
        d = self.get_district()
        if d and h:
            return f"{d} / {h}"
        return h or d or ""

    def set_value(self, value: str, city: str = "مشهد"):
        v = (value or "").strip()
        if not v:
            return
        self.set_for_city(city)
        if self._mashhad_mode and " / " in v:
            d, h = v.split(" / ", 1)
            if self.district_combo.findText(d) >= 0:
                self.district_combo.setCurrentText(d)
                if self.hood_combo.findText(h) >= 0:
                    self.hood_combo.setCurrentText(h)
                else:
                    self.hood_combo.setCurrentText(OTHER)
                    self.hood_other_input.setVisible(True)
                    self.hood_other_input.setText(h)
                return
        # غیر مشهد یا فرمت شناخته‌نشده → در plain
        if not self._mashhad_mode:
            self.plain_input.setText(v)
        else:
            self.hood_combo.setCurrentText(OTHER)
            self.hood_other_input.setVisible(True)
            self.hood_other_input.setText(v)