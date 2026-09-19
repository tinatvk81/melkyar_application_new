from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QTableWidget, QStackedWidget, QWidget, QVBoxLayout


class TableSpinner:
    """پوشش شفاف روی جدول حین fetch — راه‌اندازی: show(table) / hide(table).
    بدون قفل‌کردن UI؛ فقط بازخورد بصری می‌دهد."""

    _labels = {}  # table -> QLabel

    @staticmethod
    def show(table: QTableWidget, text: str = "⏳ در حال دریافت..."):
        TableSpinner.hide(table)
        lbl = QLabel(text, table.viewport())
        lbl.setStyleSheet(
            "QLabel { background: rgba(11,13,23,0.55); color: #f5a623;"
            " border-radius: 12px; padding: 14px 34px; font-weight: bold;"
            " border: 1px solid rgba(245,166,35,0.45); }")
        lbl.adjustSize()
        vw, vh = table.viewport().width(), table.viewport().height()
        lbl.move(max(10, (vw - lbl.width()) // 2), max(10, (vh - lbl.height()) // 2))
        lbl.show()
        lbl.raise_()
        TableSpinner._labels[id(table)] = lbl
        # اگر fetch خیلی سریع بود، اسپینر فلش نزند:
        lbl._min_show = True

    @staticmethod
    def hide(table: QTableWidget):
        lbl = TableSpinner._labels.pop(id(table), None)
        if lbl:
            lbl.deleteLater()