from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QMessageBox, QFrame, QSizePolicy, QGraphicsDropShadowEffect,
    QGridLayout, QApplication, QToolButton,
)
from PySide6.QtGui import QColor
from PySide6.QtCore import QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QToolButton
from api_client import api_client, ApiError
import settings_manager

WINDOW_QSS = """
#loginRoot {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 #0b0d17, stop:0.55 #14111f, stop:1 #1c1430);
}
#brandPanel { background: transparent; }
#brandLogo {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 #f5a623, stop:1 #f97316);
    border-radius: 22px;
}
#brandTitle { color: #f5a623; font-size: 34px; font-weight: 800; background: transparent; }
#brandTag   { color: rgba(236,234,244,0.75); font-size: 13px; background: transparent; }
#featureCard {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 14px;
}
#featureCard:hover { border: 1px solid rgba(245,166,35,0.45); }
#featureIcon  { font-size: 22px; background: transparent; }
#featureTitle { color: #eceaf4; font-size: 12px; font-weight: bold; background: transparent; }
#featureSub   { color: rgba(236,234,244,0.55); font-size: 10px; background: transparent; }

#loginCard {
    background: #14111f;
    border: 1px solid rgba(245,166,35,0.28);
    border-radius: 18px;
}
#loginTitle { color: #eceaf4; font-size: 20px; font-weight: 800; background: transparent; }
#loginSub   { color: rgba(236,234,244,0.55); font-size: 11px; background: transparent; }
#fieldLabel { color: rgba(236,234,244,0.75); font-size: 11px; background: transparent; }
QLineEdit {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.13);
    border-radius: 10px; padding: 10px 14px;
    color: #eceaf4; selection-background-color: #f5a623;
}
QLineEdit:focus { border: 1px solid #f5a623; background: rgba(245,166,35,0.07); }
#loginBtn {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #f5a623, stop:1 #f97316);
    border: none; border-radius: 10px; padding: 12px;
    color: #241300; font-size: 14px; font-weight: 800;
}
#loginBtn:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #fbb63f, stop:1 #fb8c33); }
#connBtn {
    background: transparent; border: 1px solid rgba(255,255,255,0.14);
    border-radius: 10px; padding: 8px; color: rgba(236,234,244,0.7);
}
#connBtn:hover { border-color: rgba(245,166,35,0.6); color: #f5a623; }
QCheckBox { color: rgba(236,234,244,0.7); font-size: 11px; background: transparent; }
#errorLabel { color: #f87171; font-size: 11px; background: transparent; }

#brandMore {
    color: rgba(236,234,244,0.55);
    font-size: 11px;
    background: rgba(245,166,35,0.07);
    border: 1px dashed rgba(245,166,35,0.35);
    border-radius: 12px;
    padding: 10px 14px;
}

"""

FEATURES = [
    ("📋", "فایل‌ها", "ثبت و مدیریت آسان"),
    ("📅", "قراردادها", "هشدار رو‌به‌اتمام"),
    ("💰", "پورسانت", "حسابداری دقیق"),
    ("🙋", "مشتری‌ها", "تطبیق خودکار"),
    ("💬", "گفت‌وگو", "چت داخلی و چت‌بات"),
    ("✅", "پیگیری‌ها", "یادآوری هوشمند"),
    ("🗺", "نقشه", "موقعیت هر فایل"),
    ("📄", "PDF و اکسل", "قرارداد و گزارش"),
]


class LoginWindow(QWidget):
    def __init__(self, on_success):
        super().__init__()
        self.on_success = on_success
        self.setWindowTitle("ورود به ملک‌یار")
        self.setMinimumSize(940, 580)
        self.resize(1000, 620)
        self.setStyleSheet(WINDOW_QSS)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.setObjectName("loginRoot")
        self.setObjectName("loginRoot")

        # ---------- پنل برندینگ (سمت راست در RTL) ----------
        brand = QWidget()
        brand.setObjectName("brandPanel")
        brand.setFixedWidth(470)
        bl = QVBoxLayout(brand)
        bl.setContentsMargins(48, 40, 48, 40)
        bl.addStretch(1)

        more = QLabel("✚ و ده‌ها قابلیت دیگر: بایگانی هوشمند، بکاپ خودکار، خروجی PDF، حسابداری مشارکتی…")
        more.setObjectName("brandMore")
        more.setAlignment(Qt.AlignCenter)
        more.setWordWrap(True)
        bl.addWidget(more)


        logo = QLabel("🏠")
        logo.setObjectName("brandLogo")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(84, 84)
        logo.setStyleSheet(logo.styleSheet() + "font-size: 38px;")
        bl.addWidget(logo, 0, Qt.AlignHCenter)

        t = QLabel("ملک‌یار")
        t.setObjectName("brandTitle")
        t.setAlignment(Qt.AlignCenter)
        bl.addWidget(t)
        tag = QLabel("سامانهٔ مدیریت فایل‌های ملکی\nثبت، پیگیری، معاملات و اطلاع‌یه‌ها")
        tag.setObjectName("brandTag")
        tag.setAlignment(Qt.AlignCenter)
        bl.addWidget(tag)
        bl.addSpacing(28)

        grid = QGridLayout()
        grid.setSpacing(12)
        for i, (icon, title, sub) in enumerate(FEATURES):
            card = QFrame()
            card.setObjectName("featureCard")
            card.setFixedSize(160, 84)
            cv = QVBoxLayout(card)
            cv.setContentsMargins(10, 10, 10, 10)
            ic = QLabel(icon); ic.setObjectName("featureIcon"); ic.setAlignment(Qt.AlignCenter)
            tt = QLabel(title); tt.setObjectName("featureTitle"); tt.setAlignment(Qt.AlignCenter)
            ss = QLabel(sub);   ss.setObjectName("featureSub");   ss.setAlignment(Qt.AlignCenter)
            cv.addWidget(ic); cv.addWidget(tt); cv.addWidget(ss)
            grid.addWidget(card, i // 2, i % 2, Qt.AlignHCenter)
        bl.addLayout(grid)
        bl.addStretch(2)

        # ---------- کارت ورود (سمت چپ) ----------
        card_wrap = QWidget()
        cl = QVBoxLayout(card_wrap)
        cl.addStretch(1)

        card = QFrame()
        card.setObjectName("loginCard")
        card.setFixedWidth(400)
        card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40); shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 160))
        card.setGraphicsEffect(shadow)

        cv = QVBoxLayout(card)
        cv.setContentsMargins(34, 32, 34, 28)
        cv.setSpacing(8)

        title = QLabel("ورود به ملک‌یار"); title.setObjectName("loginTitle"); title.setAlignment(Qt.AlignCenter)
        sub = QLabel("اطلاعات حساب کاربری خود را وارد کنید"); sub.setObjectName("loginSub"); sub.setAlignment(Qt.AlignCenter)
        cv.addWidget(title); cv.addWidget(sub); cv.addSpacing(12)

        cv.addWidget(self._label("نام کاربری"))
        self.username_input = QLineEdit(settings_manager.get_saved_username() or "")
        self.username_input.setPlaceholderText("مثلاً amllak")
        cv.addWidget(self.username_input)

        cv.addWidget(self._label("رمز عبور"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.handle_login)
        cv.addWidget(self.password_input)
        self._reposition_pw_btn()
        self.toggle_pw_btn = QToolButton(self.password_input)
        self.toggle_pw_btn.setText("👁")
        self.toggle_pw_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_pw_btn.setStyleSheet(
            "QToolButton { border: none; background: transparent; padding: 0 8px; }"
            "QToolButton:hover { color: #f5a623; }")
        self.toggle_pw_btn.setCheckable(True)
        self.toggle_pw_btn.setFixedHeight(self.password_input.height())
        self.toggle_pw_btn.move(
            self.password_input.width() - 34,
            (self.password_input.height() - self.toggle_pw_btn.height()) // 2)
        self.toggle_pw_btn.toggled.connect(self._toggle_password)

        self.remember_check = QCheckBox("مرا به خاطر بسپار")
        if settings_manager.get_saved_username():
            self.remember_check.setChecked(True)
        cv.addWidget(self.remember_check)

        cv.addSpacing(6)
        self.login_btn = QPushButton("ورود")
        self.login_btn.setObjectName("loginBtn")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self.handle_login)
        cv.addWidget(self.login_btn)

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        cv.addWidget(self.error_label)

        conn_btn = QPushButton("⚙️ تنظیمات اتصال")
        conn_btn.setObjectName("connBtn")
        conn_btn.setCursor(Qt.PointingHandCursor)
        conn_btn.clicked.connect(self._open_connection_settings)
        cv.addWidget(conn_btn)

        cl.addWidget(card, 0, Qt.AlignHCenter)
        cl.addStretch(1)

        # RTL: برند سمت راست، کارت سمت چپ
        root.addWidget(card_wrap, 1)
        root.addWidget(brand)

        self.username_input.setFocus()
        if settings_manager.get_saved_username() and settings_manager.load_settings().get("saved_password"):
            self.password_input.setText(settings_manager.load_settings().get("saved_password") or "")


        self._reposition_pw_btn()
    # ---------- helpers ----------
    def _label(self, text):
        l = QLabel(text); l.setObjectName("fieldLabel"); return l

    def _open_connection_settings(self):
        from ui.connection_settings_dialog import ConnectionSettingsDialog
        ConnectionSettingsDialog(self).exec()


    def _reposition_pw_btn(self):
        b = self.toggle_pw_btn
        w = self.password_input
        b.move(w.width() - b.width() - 8, (w.height() - b.height()) // 2)
        b.raise_()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self.password_input and event.type() == QEvent.Resize:
            self._reposition_pw_btn()
        return super().eventFilter(obj, event)

    def _toggle_password(self, show: bool):
        self.password_input.setEchoMode(
            QLineEdit.Normal if show else QLineEdit.Password)
        self.toggle_pw_btn.setText("🙈" if show else "👁")


    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            self._show_error("نام کاربری و رمز عبور را وارد کنید.")
            return
        self.login_btn.setEnabled(False)
        self.login_btn.setText("در حال ورود…")
        QApplication.processEvents()
        try:
            data = api_client.login(username, password)
        except ApiError as e:
            self._show_error(str(e))
            self.login_btn.setEnabled(True)
            self.login_btn.setText("ورود")
            return
        except Exception as e:
            self._show_error("اتصال به سرور برقرار نشد — تنظیمات اتصال را چک کنید.")
            self.login_btn.setEnabled(True)
            self.login_btn.setText("ورود")
            return

        # ذخیرهٔ اعتبار در صورت تیک (نکته: روی دیسک محلی است — فقط دفتر معتمد)
        if self.remember_check.isChecked():
            settings_manager.set_saved_username(username)
            s = settings_manager.load_settings()
            s["saved_password"] = password
            settings_manager.save_settings(s)
        else:
            settings_manager.set_saved_username("")
            s = settings_manager.load_settings()
            s.pop("saved_password", None)
            settings_manager.save_settings(s)

        self.on_success()

    def _show_error(self, text):
        self.error_label.setText("⚠ " + text)
        self.error_label.setVisible(True)