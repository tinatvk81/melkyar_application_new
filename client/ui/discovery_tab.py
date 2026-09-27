import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QAbstractItemView, QDialog,
    QFormLayout, QFrame,
)
from PySide6.QtGui import QColor

from api_client import api_client, ApiError
from session import handle_api_error
from ui.spinner import TableSpinner
from ui.toast import Toast
from ui.property_form import DEAL_TYPE_LABELS, PropertyFormDialog

DEAL_TYPE_FA = {"sale": "فروش", "rent": "اجاره", "mortgage": "رهن کامل", "presale": "پیش‌خرید"}


class ListingDetailDialog(QDialog):
    """جزئیات کامل یک آگهی ملک‌یاب + اقدام‌ها: باز کردن لینک / افزودن به فایل‌ها / نادیده گرفتن."""

    def __init__(self, item, on_add, on_dismiss):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.item = item
        self.on_add = on_add
        self.on_dismiss = on_dismiss
        self.setWindowTitle("جزئیات آگهی — ملک‌یاب")
        self.resize(520, 480)

        form = QFormLayout()
        form.addRow("عنوان:", QLabel(item.get("title") or "—"))
        form.addRow("منبع:", QLabel("دیوار" if item.get("source") == "divar" else (item.get("source") or "—")))
        dt = item.get("deal_type")
        form.addRow("نوع معامله:", QLabel(DEAL_TYPE_FA.get(dt, dt or "—")))

        city = item.get("city") or "—"
        district = item.get("raw_address") or "—"
        form.addRow("شهر / محله:", QLabel(f"{city} — {district}"))

        area = item.get("area_m2")
        rooms = item.get("rooms")
        form.addRow("متراژ / اتاق:", QLabel(
            f"{area} متر / {rooms} اتاق" if (area or rooms) else "—"))

        price, dep, rent = item.get("price"), item.get("deposit"), item.get("monthly_rent")
        if price:
            money = QLabel(f"{price:,} تومان"); money.setStyleSheet("font-weight:800; color:#f5a623;")
            form.addRow("قیمت کل:", money)
        elif dep and rent:
            d1 = QLabel(f"ودیعه {dep:,} — اجاره {rent:,} تومان")
            d1.setStyleSheet("font-weight:800; color:#f5a623;")
            form.addRow("اجاره:", d1)
        elif dep:
            d2 = QLabel(f"{dep:,} تومان"); d2.setStyleSheet("font-weight:800; color:#f5a623;")
            form.addRow("رهن کامل:", d2)
        else:
            form.addRow("قیمت:", QLabel("—"))

        form.addRow("تاریخ آگهی:", QLabel((item.get("posted_at") or "")[:16].replace("T", " ")))

        note = QLabel("شماره تماس مالک در خود دیوار نمایش داده می‌شود — با دکمهٔ زیر آگهی را باز کن.")
        note.setWordWrap(True)
        note.setStyleSheet("color: rgba(128,128,140,1); font-size: 10px;")

        open_btn = QPushButton("🔗 باز کردن آگهی در دیوار")
        open_btn.setObjectName("chip")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.clicked.connect(lambda: webbrowser.open(item.get("url") or "https://divar.ir"))

        add_btn = QPushButton("➕ افزودن به فایل‌های من")
        add_btn.setObjectName("primary")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add)

        dismiss_btn = QPushButton("نادیده بگیر")
        dismiss_btn.setObjectName("chip")
        dismiss_btn.clicked.connect(self._dismiss)

        btns = QHBoxLayout()
        btns.addWidget(dismiss_btn)
        btns.addStretch()
        btns.addWidget(open_btn)
        btns.addWidget(add_btn)

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(note)
        lay.addLayout(btns)

    def _add(self):
        self.accept()
        self.on_add(self.item)

    def _dismiss(self):
        self.accept()
        self.on_dismiss(self.item)


class DiscoveryTab(QWidget):
    """یافته‌های ملک‌یاب — آگهی‌های شخصیِ تازه از دیوار/شیپور؛ دابل‌کلیک = جزئیات و اقدام."""

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._listings = []

        title = QLabel("📡 یافته‌های ملک‌یاب — آگهی‌های شخصیِ تازه")
        title.setStyleSheet("font-size: 15px; font-weight: 800; color: #f5a623; background: transparent;")
        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: rgba(128,128,140,1); background: transparent;")

        refresh_btn = QPushButton("🔄 به‌روزرسانی")
        refresh_btn.setObjectName("chip")
        refresh_btn.clicked.connect(self.refresh)

        header = QHBoxLayout()
        header.addWidget(title)
        header.addSpacing(12)
        header.addWidget(self.count_label)
        header.addStretch()
        header.addWidget(refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["عنوان", "محله", "قیمت", "نوع", "منبع", "تاریخ"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setStyleSheet(
            "QTableWidget { border: none; }"
            "QTableWidget::item { padding: 6px; border-bottom: 1px solid rgba(128,128,140,0.30); }"
            "QTableWidget::item:selected { background: rgba(245,166,35,0.28); }")
        self.table.doubleClicked.connect(lambda _: self._open_detail())

        hint = QLabel("دابل‌کلیک روی هر آگهی = جزئیات کامل و افزودن به فایل‌ها")
        hint.setStyleSheet("color: rgba(128,128,140,1); background: transparent;")

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self.table)
        layout.addWidget(hint)
        self.refresh()

    def refresh(self):
        TableSpinner.show(self.table)
        try:
            self._listings = api_client.list_discovered_listings(only_new=True)
        except ApiError as e:
            TableSpinner.hide(self.table)
            handle_api_error(self, e, "خطا در دریافت یافته‌ها")
            return
        TableSpinner.hide(self.table)
        self.count_label.setText(f"{len(self._listings)} یافتهٔ جدید")
        self._render()

    def _price_text(self, it) -> str:
        if it.get("price"):
            return f"{it['price']:,}"
        if it.get("deposit") and it.get("monthly_rent"):
            return f"ودیعه {it['deposit']:,} / اجاره {it['monthly_rent']:,}"
        if it.get("deposit"):
            return f"رهن {it['deposit']:,}"
        return "—"

    def _render(self):
        self.table.setRowCount(len(self._listings))
        for row, it in enumerate(self._listings):
            self.table.setItem(row, 0, QTableWidgetItem(it.get("title") or ""))
            self.table.setItem(row, 1, QTableWidgetItem(it.get("raw_address") or "—"))
            p = QTableWidgetItem(self._price_text(it))
            p.setForeground(QColor("#f5a623"))
            f = p.font(); f.setBold(True); p.setFont(f)
            self.table.setItem(row, 2, p)
            dt = it.get("deal_type")
            self.table.setItem(row, 3, QTableWidgetItem(DEAL_TYPE_FA.get(dt, dt or "—")))
            self.table.setItem(row, 4, QTableWidgetItem("دیوار" if it.get("source") == "divar" else (it.get("source") or "")))
            self.table.setItem(row, 5, QTableWidgetItem((it.get("posted_at") or "")[:10]))

        if not self._listings:
            self.table.setRowCount(1)
            empty = QTableWidgetItem("فعلاً یافتهٔ جدیدی نیست — کراولر هر ۱۰ دقیقه چک می‌کند")
            empty.setForeground(QColor("#86efac"))
            self.table.setItem(0, 0, empty)
            self.table.setSpan(0, 0, 1, 6)

    def _selected(self):
        row = self.table.currentRow()
        if 0 <= row < len(self._listings):
            return self._listings[row]
        return None

    def _open_detail(self):
        it = self._selected()
        if not it:
            return
        ListingDetailDialog(it, on_add=self._add_to_files, on_dismiss=self._dismiss).exec()

    @staticmethod
    def _prefill_from(it: dict) -> dict:
        note_lines = [f"وارد شده از ملک‌یاب — منبع: {it.get('source')}",
                      it.get("title") or "", it.get("url") or ""]
        return {
            "deal_type": it.get("deal_type") or "sale",
            "city": it.get("city"),
            "district": it.get("raw_address"),
            "area_m2": it.get("area_m2"),
            "rooms": it.get("rooms"),
            "price": it.get("price"),
            "deposit": it.get("deposit"),
            "monthly_rent": it.get("monthly_rent"),
            "source_note": "\n".join(x for x in note_lines if x),
            "listing_id": it.get("id"),
        }

    def _add_to_files(self, it: dict):
        PropertyFormDialog(property_data=None, on_saved=self.refresh,
                           prefill=self._prefill_from(it)).exec()

    def _dismiss(self, it: dict):
        try:
            api_client.dismiss_discovery_listing(it["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        Toast.show("آگهی نادیده گرفته شد")
        self.refresh()