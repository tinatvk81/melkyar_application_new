"""تم تیرهٔ سورمه‌ای + اکسنت طلایی-نارنجی (لوکس املاک) + RTL + فونت وزیرمتن"""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtWidgets import QApplication

from resource_path import resource_path

FONT_PATH = resource_path("resources", "fonts", "Vazirmatn-Regular.ttf")

QSS = """
QWidget { color: #eceaf4; font-size: 10pt; }
QMainWindow, QDialog {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #0b0d17, stop:1 #14111f);
}
QLabel { background: transparent; }

QPushButton {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 9px; padding: 7px 16px;
}
QPushButton:hover { border-color: rgba(245,166,35,0.65); background: rgba(245,166,35,0.14); }
QPushButton:pressed { background: rgba(245,166,35,0.28); }
QPushButton:disabled { color: rgba(236,234,244,0.30); }

QPushButton#primary {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #f5a623, stop:1 #f97316);
    border: none; color: #241300; font-weight: 800; padding: 8px 24px;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #fbb63f, stop:1 #fb8c33);
}
QPushButton#primary:pressed { background: #e08c12; }

QPushButton#chip {
    background: rgba(255,255,255,0.06);
    border-radius: 14px; padding: 5px 14px;
}
QPushButton#chip:hover { border-color: rgba(245,166,35,0.6); }

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.13);
    border-radius: 8px; padding: 6px 10px;
    selection-background-color: #f5a623; selection-color: #241300;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #f5a623; background: rgba(245,166,35,0.08);
}
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background: #171426; border: 1px solid rgba(245,166,35,0.4);
    selection-background-color: rgba(245,166,35,0.30); border-radius: 6px;
}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background: rgba(255,255,255,0.06); border: none; width: 18px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background: rgba(245,166,35,0.35);
}
QAbstractSpinBox { min-width: 90px; padding: 6px 8px; }

QTableWidget {
    background: transparent; alternate-background-color: rgba(255,255,255,0.03);
    gridline-color: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.10); border-radius: 10px;
}
QTableWidget::item { padding: 6px; }
QTableWidget::item:selected { background: rgba(245,166,35,0.32); }
QHeaderView::section {
    background: rgba(255,255,255,0.06); border: none;
    border-bottom: 2px solid rgba(245,166,35,0.45); padding: 8px;
}

QTabWidget::pane { border: 1px solid rgba(255,255,255,0.10); border-radius: 10px; top: -1px; }
QTabBar::tab {
    background: transparent; padding: 8px 16px; margin: 3px;
    border-radius: 8px; color: rgba(236,234,244,0.65);
}
QTabBar::tab:selected {
    background: rgba(245,166,35,0.18); color: #ffffff; font-weight: 700;
    border: 1px solid rgba(245,166,35,0.5);
}
QTabBar::tab:hover { background: rgba(255,255,255,0.07); }

QCheckBox { spacing: 7px; }
QCheckBox::indicator {
    width: 17px; height: 17px; border-radius: 5px;
    border: 1px solid rgba(255,255,255,0.28); background: rgba(255,255,255,0.05);
}
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #f5a623, stop:1 #f97316);
    border-color: transparent;
}

QListWidget { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.11); border-radius: 8px; }
QListWidget::item { padding: 5px; border-radius: 5px; }
QListWidget::item:selected { background: rgba(245,166,35,0.32); }
QListWidget#chipList { background: transparent; border: none; }
QListWidget#chipList::item {
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.16);
    border-radius: 13px; padding: 5px 14px; margin: 3px;
}
QListWidget#chipList::item:hover { border-color: rgba(245,166,35,0.6); }
QListWidget#chipList::item:selected {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #f5a623, stop:1 #f97316);
    border-color: transparent; color: #241300;
}

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: rgba(255,255,255,0.18); border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: rgba(245,166,35,0.5); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: rgba(255,255,255,0.18); border-radius: 5px; min-width: 30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QToolTip { background: #1c1830; border: 1px solid rgba(245,166,35,0.5); padding: 6px; border-radius: 6px; }
QMessageBox { background: #12101e; }
QMenu { background: #171426; border: 1px solid rgba(255,255,255,0.14); border-radius: 8px; }
QMenu::item { padding: 7px 22px; }
QMenu::item:selected { background: rgba(245,166,35,0.35); }

QFrame#statCard {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 14px;
}
QFrame#statCard:hover { border: 1px solid rgba(245,166,35,0.55); }
QFrame#statCard QLabel { background: transparent; }

QListWidget#sideNav {
    background: rgba(255,255,255,0.03);
    border: none; border-inline-start: 1px solid rgba(255,255,255,0.08);
    padding: 10px 6px; outline: none;
}
QListWidget#sideNav::item {
    color: rgba(236,234,244,0.70);
    border-radius: 10px; padding: 11px 14px; margin: 3px 6px;
}
QListWidget#sideNav::item:hover { background: rgba(255,255,255,0.06); color: #ffffff; }
QListWidget#sideNav::item:selected {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 rgba(245,166,35,0.28), stop:1 rgba(249,115,22,0.14));
    color: #ffd08a; font-weight: 700;
    border-inline-end: 3px solid #f5a623;
}
QLabel#sideTitle {
    font-size: 13px; font-weight: 800; color: #f5a623;
    padding: 8px 14px 4px; background: transparent;
}
QLabel#bellLabel {
    background: rgba(245,166,35,0.10); border: 1px solid rgba(245,166,35,0.4);
    border-radius: 10px; padding: 9px; margin: 6px 10px;
}

"""


def apply_persian_rtl_style(app: QApplication):
    app.setLayoutDirection(Qt.RightToLeft)

    if os.path.exists(FONT_PATH):
        font_id = QFontDatabase.addApplicationFont(FONT_PATH)
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            app.setFont(QFont(families[0], 10))
    else:
        app.setFont(QFont("Tahoma", 10))

    app.setStyleSheet(QSS)