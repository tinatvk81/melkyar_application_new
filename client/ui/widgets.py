# -*- coding: utf-8 -*-
"""ویجت‌های عمومی: ارقام فارسی، تلفن، امکانات دلخواه، هایلایت جست‌وجو، چیپ فیلتر"""
import re
from html import escape

from PySide6.QtCore import Qt, QRegularExpression, Signal
from PySide6.QtGui import QValidator, QRegularExpressionValidator, QTextDocument, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QSpinBox, QDoubleSpinBox, QLineEdit, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QListView, QMessageBox,
    QStyledItemDelegate, QStyle, QStyleOptionViewItem, QApplication,
)

PERSIAN = "۰۱۲۳۴۵۶۷۸۹"
ARABIC = "٠١٢٣٤٥٦٧٨٩"
_TABLE = str.maketrans(PERSIAN + ARABIC, "0123456789" * 2)


def to_english_digits(text: str) -> str:
    return (text or "").translate(_TABLE)


class PersianSpinBox(QSpinBox):
    """تایپ دستی + دکمهٔ بالا/پایین + پذیرش ارقام فارسی"""

    def __init__(self, minimum=0, maximum=10_000_000, parent=None):
        super().__init__(parent)
        self.setRange(minimum, maximum)
        self.setAccelerated(True)

    def validate(self, text, pos):
        conv = to_english_digits(text)
        if conv.strip() == "":
            return QValidator.Intermediate, text, pos
        state, _, _ = super().validate(conv, pos)
        return state, text, pos

    def valueFromText(self, text):
        try:
            return int(to_english_digits(text).strip() or 0)
        except ValueError:
            return self.minimum()


class PersianDoubleSpinBox(QDoubleSpinBox):
    """مثل بالا ولی اعشاری (برای متراژ)"""

    def __init__(self, minimum=0.0, maximum=100000.0, decimals=1, suffix="", parent=None):
        super().__init__(parent)
        self.setRange(minimum, maximum)
        self.setDecimals(decimals)
        if suffix:
            self.setSuffix(suffix)
        self.setAccelerated(True)

    def validate(self, text, pos):
        conv = to_english_digits(text)
        if conv.strip() in ("", self.suffix().strip()):
            return QValidator.Intermediate, text, pos
        state, _, _ = super().validate(conv, pos)
        return state, text, pos

    def valueFromText(self, text):
        t = to_english_digits(text).replace(self.suffix(), "").strip()
        t = t.replace("،", "").replace(",", "")
        try:
            return float(t) if t else self.minimum()
        except ValueError:
            return self.minimum()


class MoneyLineEdit(QLineEdit):
    """مبلغ: فقط رقم، ارقام فارسی هم قبول، جداکنندهٔ هزارگان خودکار"""

    def __init__(self, placeholder="مثلاً 5200000000"):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setAlignment(Qt.AlignRight)
        self.editingFinished.connect(self._format)

    def value(self):
        t = to_english_digits(self.text()).replace(",", "").replace(" ", "").strip()
        if not t:
            return None
        if not t.isdigit():
            raise ValueError("مبلغ باید فقط عدد باشد")
        return int(t)

    def set_value(self, v):
        self.setText(f"{int(v):,}" if v is not None else "")

    def _format(self):
        try:
            v = self.value()
        except ValueError:
            return
        self.setText(f"{v:,}" if v is not None else "")


class PhoneLineEdit(QLineEdit):
    """تلفن: فقط رقم فارسی/انگلیسی و + ؛ خروج به شکل استاندارد 09..."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setValidator(QRegularExpressionValidator(
            QRegularExpression(r"^[0-9۰-۹٠-٩+ ]*$"), self))
        self.editingFinished.connect(lambda: self.setText(self.normalized_text()))

    def normalized_text(self) -> str:
        d = to_english_digits(self.text()).replace(" ", "")
        if d.startswith("+98"):
            d = "0" + d[3:]
        elif d.startswith("98") and len(d) >= 12:
            d = "0" + d[2:]
        return d

    def is_valid(self) -> bool:
        d = self.normalized_text()
        return d.isdigit() and 10 <= len(d) <= 11


class TagInputWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("مورد دلخواه را بنویسید و Enter بزنید…")
        add_btn = QPushButton("افزودن")
        top.addWidget(self.entry, 1)
        top.addWidget(add_btn)
        self.listw = QListWidget()
        self.listw.setObjectName("chipList")
        self.listw.setViewMode(QListWidget.IconMode)
        self.listw.setFlow(QListView.LeftToRight)
        self.listw.setWrapping(True)
        self.listw.setResizeMode(QListView.Adjust)
        self.listw.setSelectionMode(QListWidget.MultiSelection)
        self.listw.setMaximumHeight(84)
        self.listw.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        del_btn = QPushButton("حذف چیپ‌های انتخاب‌شده")
        lay.addLayout(top)
        lay.addWidget(self.listw)
        lay.addWidget(del_btn)
        add_btn.clicked.connect(self._add)
        self.entry.returnPressed.connect(self._add)
        del_btn.clicked.connect(self._remove_selected)

    def _add(self):
        t = self.entry.text().strip()
        if not t:
            return
        if self.listw.findItems(t, Qt.MatchExactly):
            QMessageBox.information(self, "تکراری", f"«{t}» قبلاً اضافه شده است.")
            return
        item = QListWidgetItem(t)
        self.listw.addItem(item)
        item.setSelected(True)  # چیپ جدید از همان اول فعال است
        self.entry.clear()

    def _remove_selected(self):
        for item in self.listw.selectedItems():
            self.listw.takeItem(self.listw.row(item))

    def set_tags(self, tags):
        self.listw.clear()
        for t in (tags or []):
            item = QListWidgetItem(t)
            self.listw.addItem(item)
            item.setSelected(True)

    def get_tags(self):
        return [i.text() for i in self.listw.selectedItems()]

class MatchHighlightDelegate(QStyledItemDelegate):
    """متن تطبیق‌یافتهٔ جست‌وجو را در سلول‌های جدول رنگی برجسته می‌کند"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._term = ""

    def set_term(self, term: str):
        self._term = (term or "").strip()

    def paint(self, painter, option, index):
        if not self._term:
            super().paint(painter, option, index)
            return
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        text = opt.text
        opt.text = ""
        style = opt.widget.style() if opt.widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, opt, painter, opt.widget)
        pattern = re.compile(re.escape(self._term), re.IGNORECASE)
        html = pattern.sub(
            lambda m: f"<span style='color:#9db1ff; font-weight:700;'>{escape(m.group(0))}</span>",
            escape(text))
        doc = QTextDocument()
        doc.setDefaultFont(opt.font)
        doc.setHtml(html)
        doc.setTextWidth(max(10, opt.rect.width() - 12))
        painter.save()
        y = opt.rect.top() + (opt.rect.height() - doc.size().height()) / 2
        painter.translate(opt.rect.left() + 6, y)
        doc.drawContents(painter)
        painter.restore()


class QuickFilterBar(QWidget):
    """چیپ‌های فیلتر آماده — با هر کلیک سیگنال می‌فرستد"""
    filter_selected = Signal(str, object)

    PRESETS = [
        ("همه", None, None),
        ("فروش", "deal_type", "sale"),
        ("اجاره", "deal_type", "rent"),
        ("رهن کامل", "deal_type", "mortgage"),
        ("پیش‌خرید", "deal_type", "presale"),
        ("فروش زیر ۲ میلیارد", "max_price_sale", 2_000_000_000),
        ("متراژ ۱۰۰+", "min_area", 100),
        ("آسانسور", "has_elevator", True),
        ("پارکینگ", "has_parking", True),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        for label, key, value in self.PRESETS:
            b = QPushButton(label)
            b.setObjectName("chip")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key, v=value: self.filter_selected.emit(k, v))
            row.addWidget(b)
        row.addStretch(1)


def bind_ctrl_f(window, target: QLineEdit):
    """Ctrl+F → فوکوس روی کادر جست‌وجو و انتخاب متن"""
    sc = QShortcut(QKeySequence.Find, window)
    sc.activated.connect(lambda: (target.setFocus(), target.selectAll()))