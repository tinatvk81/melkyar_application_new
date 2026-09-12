from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QFont, QPainterPath
from PySide6.QtWidgets import QWidget


def _fa_num(n):
    return f"{int(n):,}" if n >= 1000 else str(int(n))


class BarChart(QWidget):
    """نمودار ستونی عمودی — برای معامله‌های ماهانه"""

    def __init__(self, money=False, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(170)
        self._labels, self._values = [], []
        self._money = money

    def set_data(self, labels, values):
        self._labels, self._values = labels, values
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), Qt.transparent)
        if not self._values:
            p.setPen(QColor(150, 160, 200))
            p.drawText(self.rect(), Qt.AlignCenter, "داده‌ای نیست")
            return
        w, h = self.width(), self.height()
        bottom = h - 22
        vmax = max(self._values) or 1
        n = len(self._values)
        gap = 10
        bw = max(8, (w - gap * (n + 1)) / n)
        font = QFont()
        font.setPointSize(7)
        p.setFont(font)
        for i, v in enumerate(self._values):
            x = w - gap - (i + 1) * bw - i * gap  # از راست (RTL)
            bh = 0 if vmax == 0 else (v / vmax) * (bottom - 18)
            grad = QLinearGradient(x, bottom - bh, x, bottom)
            grad.setColorAt(0, QColor("#8b5cf6"))
            grad.setColorAt(1, QColor("#4f46e5"))
            p.setBrush(grad)
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(x, bottom - bh, bw, bh), 4, 4)
            p.setPen(QColor(220, 226, 255))
            label = _fa_num(v) if self._money else str(int(v))
            p.drawText(QRectF(x - 6, bottom - bh - 15, bw + 12, 14), Qt.AlignCenter, label)
            p.setPen(QColor(140, 150, 190))
            p.drawText(QRectF(x - 6, bottom + 3, bw + 12, 16), Qt.AlignCenter, self._labels[i])


class HBarChart(QWidget):
    """نمودار میله‌ای افقی — برای سهم مشاوران"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []  # (label, value)

    def set_data(self, rows):
        self._rows = rows
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if not self._rows:
            p.setPen(QColor(150, 160, 200))
            p.drawText(self.rect(), Qt.AlignCenter, "داده‌ای نیست")
            return
        vmax = max(v for _, v in self._rows) or 1
        row_h = 26
        font = QFont(); font.setPointSize(8)
        p.setFont(font)
        y = 4
        label_w = 110
        for label, v in self._rows:
            bar_w = (self.width() - label_w - 70) * (v / vmax) if vmax else 0
            p.setPen(QColor(220, 226, 255))
            p.drawText(QRectF(0, y, label_w - 6, row_h), Qt.AlignVCenter | Qt.AlignRight, str(label))
            grad = QLinearGradient(label_w, 0, self.width(), 0)
            grad.setColorAt(0, QColor("#6366f1"))
            grad.setColorAt(1, QColor("#a78bfa"))
            p.setBrush(grad); p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(label_w, y + 5, max(bar_w, 4), row_h - 10), 5, 5)
            p.setPen(QColor(160, 200, 255))
            p.drawText(QRectF(label_w + max(bar_w, 4) + 4, y, 80, row_h), Qt.AlignVCenter, f"{v:,}")
            y += row_h
        self.setMinimumHeight(y + 6)