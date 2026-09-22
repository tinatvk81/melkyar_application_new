# -*- coding: utf-8 -*-
"""ویجت‌های عمومی: ارقام فارسی، تلفن، امکانات دلخواه، هایلایت جست‌وجو، چیپ فیلتر"""
import re
from html import escape
from PySide6.QtCore import Qt, QRegularExpression, Signal
from PySide6.QtWidgets import (
    QSpinBox, QDoubleSpinBox, QLineEdit, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QListView, QMessageBox,
    QStyledItemDelegate, QStyle, QStyleOptionViewItem, QApplication,
)
from number_to_words import money_to_words
from PySide6.QtGui import QValidator, QRegularExpressionValidator, QTextDocument, QKeySequence, QShortcut, QColor

PERSIAN = "۰۱۲۳۴۵۶۷۸۹"
ARABIC = "٠١٢٣٤٥٦٧٨٩"
_TABLE = str.maketrans(PERSIAN + ARABIC, "0123456789" * 2)
# رنگ‌های آواتار مشترک — همهٔ صفحات از این استفاده می‌کنند تا رنگ هر نفر ثابت بماند
AVATAR_COLORS = ["#f5a623", "#7dd3fc", "#86efac", "#c4b5fd", "#fca5a5", "#2dd4bf", "#fdba74"]

def to_english_digits(text: str) -> str:
    return (text or "").translate(_TABLE)


class PersianSpinBox(QSpinBox):
    """تایپ دستی + دکمهٔ بالا/پایین + پذیرش ارقام فارسی.
    UX: با ورود فوکوس، اگر مقدار صفر بود خودکار پاک می‌شود تا «۰۲» نشود («۲»)."""

    def __init__(self, minimum=0, maximum=10_000_000, parent=None):
        super().__init__(parent)
        self.setRange(minimum, maximum)
        self.setAccelerated(True)
        self.setMinimumWidth(110)
        self.setStyleSheet("QAbstractSpinBox { min-width: 90px; padding: 6px 8px; }")
        self.setKeyboardTracking(False)  # تغییر فقط با Enter/فوکوس‌خروج اعمال شود، نه هر کلید
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        # با ورود فوکوس (کلیک یا Tab): اگر مقدار صفر/خالی است، متن را انتخاب کن
        # تا اولین رقمِ تایپ‌شده جایگزین شود — نه اینکه جلوِ صفر بنشیند.
        from PySide6.QtCore import QEvent
        if obj is self and event.type() == QEvent.FocusIn:
            if self.value() == 0:
                self.lineEdit().clear()
            else:
                self.lineEdit().selectAll()
        return super().eventFilter(obj, event)

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
    """اعشاری (متراژ و...) — تایپ مستقیم پس از کلیک؛ صفر اولیه پاک می‌شود؛
    suffix فقط وقتی فوکوس نیست نمایش داده می‌شود تا تایپ خراب نشود."""

    def __init__(self, minimum=0.0, maximum=100000.0, decimals=1, suffix="", parent=None):
        super().__init__(parent)
        self.setRange(minimum, maximum)
        self.setMinimumWidth(110)
        self.setStyleSheet("QAbstractSpinBox { min-width: 90px; padding: 6px 8px; }")
        self.setDecimals(decimals)
        self._suffix = suffix or ""
        self.setAccelerated(True)
        self.setKeyboardTracking(False)
        self.setSpecialValueText(" ")          # مقدار حداقل = خالی دیده شود
        self.setGroupSeparatorShown(False)

    def focusInEvent(self, event):
        # suffix را بردار و متن خالی/انتخاب‌شده بگذار تا تایپ از نو شروع شود
        if self._suffix:
            self.setSuffix("")
        if float(self.value()) == float(self.minimum()):
            self.lineEdit().clear()
        else:
            self.lineEdit().selectAll()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if self._suffix:
            self.setSuffix(self._suffix)   # برگرداندن suffix بعد از خروج

    def validate(self, text, pos):
        conv = to_english_digits(text)
        if conv.strip() in ("", self.suffix().strip()):
            return QValidator.Intermediate, text, pos
        state, _, _ = super().validate(conv, pos)
        return state, text, pos

    def valueFromText(self, text):
        t = to_english_digits(text).replace(self._suffix, "").strip()
        t = t.replace("،", "").replace(",", "")
        try:
            return float(t) if t else self.minimum()
        except ValueError:
            return self.minimum()

class MoneyLineEdit(QLineEdit):
    """مبلغ: فقط رقم، ارقام فارسی هم قبول، جداکنندهٔ هزارگان خودکار
    + لیبل زندهٔ «به حروف» زیر فیلد."""

    def __init__(self, placeholder="مثلاً 5200000000"):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setAlignment(Qt.AlignRight)
        self.editingFinished.connect(self._format)

        # لیبل حروف — والد همان فرم است؛ با textChanged آپدیت می‌شود
        self.words_label = None
        self.textChanged.connect(self._update_words)
        self._install_words_label()


    def ensure_words_label(self):
        """اگر لیبل حروف هنوز ساخته نشده (چون موقع init هنوز به layout اضافه نشده بود)، حالا بساز."""
        if self.words_label is None:
            self._install_words_label()


    def _install_words_label(self):
        """لیبل حروف را درست زیر خود فیلد جا می‌دهد — با پیدا کردن layout مستقیم.
        QFormLayout → insertRow؛ بقیه → insertWidget."""
        try:
            from PySide6.QtWidgets import QLabel, QFormLayout
            parent = self.parentWidget()
            if parent is None:
                return
            lay = self._find_own_layout(parent.layout())
            if lay is None:
                return
            if self.words_label is None:
                self.words_label = QLabel("")
                self.words_label.setStyleSheet(
                    "color: #7dd3fc; background: transparent; font-size: 9px; border: none;")
                self.words_label.setWordWrap(True)
                self.words_label.setVisible(False)
            if isinstance(lay, QFormLayout):
                row, _role = lay.getWidgetPosition(self)
                if row >= 0:
                    lay.insertRow(row + 1, self.words_label)
            else:
                idx = lay.indexOf(self)
                lay.insertWidget(idx + 1, self.words_label)
        except Exception:
            self.words_label = None

    def _find_own_layout(self, layout):
        """بازگشتی: layoutی که مستقیم self را دارد (فیلد داخل QFormLayout یا VBox تو در تو)."""
        if layout is None:
            return None
        if layout.indexOf(self) != -1:
            return layout
        for i in range(layout.count()):
            sub = layout.itemAt(i).layout()
            if sub is not None:
                found = self._find_own_layout(sub)
                if found is not None:
                    return found
        return None


    def _update_words(self):
        if self.words_label is None:
            return
        try:
            v = self.value()
        except ValueError:
            self.words_label.setVisible(False)
            return
        if v:
            self.words_label.setText("✍️ " + money_to_words(v))
            self.words_label.setVisible(True)
        else:
            self.words_label.setVisible(False)

    def value(self):
        t = to_english_digits(self.text()).replace(",", "").replace(" ", "").strip()
        if not t:
            return None
        if not t.isdigit():
            raise ValueError("مبلغ باید فقط عدد باشد")
        return int(t)

    def set_value(self, v):
        self.setText(f"{int(v):,}" if v is not None else "")
        self._update_words()

    def _format(self):
        try:
            v = self.value()
        except ValueError:
            return
        self.setText(f"{v:,}" if v is not None else "")
        self._update_words()

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
        # رنگ سفارشی سلول (بج نوع معامله، قیمت طلایی و…) هنگام هایلایت جست‌وجو حفظ شود
        fg = index.data(Qt.ForegroundRole)
        base_css = ""
        if fg is not None:
            try:
                base_css = f"color:{(fg.color() if hasattr(fg, 'color') else fg).name()};"
            except Exception:
                base_css = ""
        pattern = re.compile(re.escape(self._term), re.IGNORECASE)
        html = pattern.sub(
            lambda m: f"<span style='color:#9db1ff; font-weight:700;'>{escape(m.group(0))}</span>",
            f"<span style='{base_css}'>{escape(text)}</span>")
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
    """نوار چیپ‌های فیلتر — همه از دیتابیس (مدیریت از سایر +)"""
    preset_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(0, 0, 0, 0)
        self.reload()

    def reload(self):
        while self._row.count():
            item = self._row.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        try:
            from api_client import api_client
            presets = api_client.list_filter_presets()
        except Exception:
            presets = []
        for p in presets:
            b = QPushButton(p["name"])
            b.setObjectName("chip")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, pr=dict(p.get("params") or {}): self.preset_selected.emit(pr))
            self._row.addWidget(b)
        other = QPushButton("سایر +")
        other.setObjectName("chip")
        other.setCursor(Qt.PointingHandCursor)
        other.clicked.connect(self._open_manage)
        self._row.addWidget(other)
        self._row.addStretch(1)

    def _open_manage(self):
        from ui.preset_request_dialog import PresetRequestDialog
        PresetRequestDialog().exec()
        self.reload()

        




PROPERTY_TYPES = [
    ("apartment", "آپارتمان"), ("villa", "ویلایی"), ("old_house", "خانهٔ قدیمی"),
    ("land", "زمین"), ("demolishable", "کلنگی"), ("commercial_office", "تجاری/اداری"),
    ("shop", "مغازه"), ("office", "دفتر کار"), ("workshop", "سوله/انبار/کارگاه"),
    ("educational", "آموزشی"), ("garden", "باغ/باغچه"), ("industrial", "صنعتی"), ("other", "سایر"),
]


class PropertyTypeSelector(QWidget):
    """انتخاب چندتایی نوع ملک — چیپ‌های toggle‌شونده"""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.listw = QListWidget()
        self.listw.setObjectName("chipList")
        self.listw.setViewMode(QListWidget.IconMode)
        self.listw.setFlow(QListView.LeftToRight)
        self.listw.setWrapping(True)
        self.listw.setResizeMode(QListView.Adjust)
        self.listw.setSelectionMode(QListWidget.MultiSelection)
        self.listw.setMaximumHeight(76)
        self.listw.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for key, label in PROPERTY_TYPES:
            self.listw.addItem(QListWidgetItem(label))
            self.listw.item(self.listw.count() - 1).setData(Qt.UserRole, key)
        lay.addWidget(self.listw)

    def set_selected(self, keys: list):
        for i in range(self.listw.count()):
            it = self.listw.item(i)
            it.setSelected(it.data(Qt.UserRole) in (keys or []))

    def get_selected_keys(self) -> list:
        return [self.listw.item(i).data(Qt.UserRole)
                for i in range(self.listw.count()) if self.listw.item(i).isSelected()]

    def get_selected_labels(self) -> list:
        return [self.listw.item(i).text()
                for i in range(self.listw.count()) if self.listw.item(i).isSelected()]


                
def bind_ctrl_f(window, target: QLineEdit):
    """Ctrl+F → فوکوس روی کادر جست‌وجو و انتخاب متن"""
    sc = QShortcut(QKeySequence.Find, window)
    sc.activated.connect(lambda: (target.setFocus(), target.selectAll()))