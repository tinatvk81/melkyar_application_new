from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFrame, QLabel, QPushButton, QComboBox,
)
from PySide6.QtWidgets import QSizePolicy
from api_client import api_client, ApiError
from session import handle_api_error
from ui.property_form import DEAL_TYPE_LABELS, PropertyFormDialog

STATUS_BADGE = {"active": ("فعال", "#86efac"), "sold": ("فروخته‌شده", "#f5a623"), "inactive": ("غیرفعال", "#fca5a5")}
URGENT_FA = "🔥 فوری"


class PropertyCard(QFrame):
    clicked_id = Signal(int)

    def __init__(self, prop, thumb_loader):
        super().__init__()
        self.prop = prop
        self.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);"
            " border-radius: 14px; }"
            "QFrame:hover { border: 1px solid rgba(245,166,35,0.6); }"
            "QLabel { background: transparent; border: none; }")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(250)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy().Expanding,
                           self.sizePolicy().verticalPolicy().Fixed)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)

        # --- عکس ---
        img = QLabel()
        img.setFixedHeight(130)
        img.setAlignment(Qt.AlignCenter)
        img.setStyleSheet("background: rgba(255,255,255,0.04); border-radius: 10px;")
        if prop.get("cover_image_id"):
            pm = thumb_loader(prop["id"], prop["cover_image_id"])
            if pm:
                img.setPixmap(pm)
            else:
                img.setText("🏠")
        else:
            img.setText("🏠")
        lay.addWidget(img)

        # --- عنوان (شهر + منطقه) ---
        title = QLabel(f"{prop.get('city') or '—'}" + (f" — {prop['district']}" if prop.get("district") else ""))
        title.setStyleSheet("font-weight: bold; font-size: 12px;")
        title.setWordWrap(True)
        lay.addWidget(title)

        # --- قیمت (از سرور: قالب درست بسته به نوع معامله) ---
        price = QLabel(prop.get("price_display") or "توافقی")
        price.setStyleSheet("font-weight: 800; font-size: 13px; color: #f5a623;")
        price.setWordWrap(True)
        lay.addWidget(price)

        # --- مشخصات ریز ---
        specs = QLabel(f"📐 {prop.get('area_m2') or '—'} متر | 🛏 {prop.get('rooms') or '—'} اتاق | "
                       f"{DEAL_TYPE_LABELS.get(prop.get('deal_type'), '')}"
                       + (f" | 📅 {prop['contract_end_date']}" if prop.get("contract_end_date") else ""))
        specs.setStyleSheet("color: rgba(236,234,244,0.65); font-size: 10px;")
        specs.setWordWrap(True)
        lay.addWidget(specs)

        # --- برچسب وضعیت + فوری ---
        badge_row = QHBoxLayout()
        status, color = STATUS_BADGE.get(prop.get("status"), ("فعال", "#86efac"))
        st = QLabel(f"● {status}")
        st.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold;")
        badge_row.addWidget(st)
        if prop.get("contract_end_date"):
            from datetime import date
            try:
                y, m, dd = (int(x) for x in prop["contract_end_date"].split("-"))
                days = (date(y, m, dd) - date.today()).days
                if 0 <= days <= 7:
                    u = QLabel(URGENT_FA)
                    u.setStyleSheet("color: #fca5a5; font-size: 10px; font-weight: 800;")
                    badge_row.addWidget(u)
            except Exception:
                pass
        badge_row.addStretch()
        lay.addLayout(badge_row)

    def mousePressEvent(self, event):
        self.clicked_id.emit(self.prop["id"])
        super().mousePressEvent(event)


class PropertyCardView(QWidget):
    """نمای کارتی فایل‌ها — مثل دیوار"""

    def __init__(self, thumb_loader, on_open):
        super().__init__()
        self._thumb_loader = thumb_loader
        self._on_open = on_open
        self._items = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("مرتب‌سازی:"))
        self.sort_combo = QComboBox()
        for v, l in [("newest", "جدیدترین"), ("price_desc", "گران‌ترین"), ("price_asc", "ارزان‌ترین"),
                     ("area_desc", "بیشترین متراژ")]:
            self.sort_combo.addItem(l, v)
        bar.addWidget(self.sort_combo)
        bar.addStretch()
        outer.addLayout(bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.holder = QWidget()
        self.grid = QGridLayout(self.holder)
        self.grid.setContentsMargins(6, 6, 6, 6)
        self.grid.setSpacing(10)
        self.scroll.setWidget(self.holder)
        outer.addWidget(self.scroll, 1)

        # کارت‌ها همیشه کل عرض را پوشش دهند (RTL: ستون‌ها به سمت چپ گسترش)
        for c in range(3):
            self.grid.setColumnStretch(c, 1)

    def load(self, **filters):
        try:
            resp = api_client.list_properties(page=1, page_size=100, **filters)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        items = resp["items"]
        mode = self.sort_combo.currentData()

        def price_of(p):
            d = p.get("details") or {}
            return d.get("price") or d.get("total_price") or d.get("deposit_full") or d.get("monthly_rent") or 0
        if mode == "price_desc":
            items.sort(key=lambda p: price_of(p), reverse=True)
        elif mode == "price_asc":
            items.sort(key=lambda p: price_of(p))
        elif mode == "area_desc":
            items.sort(key=lambda p: p.get("area_m2") or 0, reverse=True)

        self._items = items
        # پاک‌سازی گرید
        while self.grid.count():
            it = self.grid.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        cols = 3
        for i, p in enumerate(items):
            card = PropertyCard(p, self._thumb_loader)
            card.clicked_id.connect(self._open)
            self.grid.addWidget(card, i // cols, i % cols)
        self.grid.setRowStretch(self.grid.rowCount(), 1)
        self.grid.setColumnStretch(cols, 1)

    def _open(self, pid):
        prop = next((p for p in self._items if p["id"] == pid), None)
        if prop:
            self._on_open(prop)