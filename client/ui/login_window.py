from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QLabel,
    QMessageBox, QCheckBox
)

from api_client import api_client, ApiError
from ui.connection_settings_dialog import ConnectionSettingsDialog
import settings_manager

try:
    import keyring
    KEYRING_OK = True
except Exception:
    KEYRING_OK = False

KEYRING_SERVICE = "MelkyarApp"


class LoginWindow(QWidget):
    def __init__(self, on_success):
        super().__init__()
        self.on_success = on_success
        self.setWindowTitle("ورود به سامانه‌ی مدیریت فایل‌های ملکی")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(380, 320)

        self.username_input = QLineEdit()
        self.username_input.setAlignment(Qt.AlignRight)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setAlignment(Qt.AlignRight)

        # Enter: یوزر → رمز → ورود
        self.username_input.returnPressed.connect(self.password_input.setFocus)
        self.password_input.returnPressed.connect(self.handle_login)

        # بازیابی ذخیره‌شده
        saved_user = settings_manager.get_saved_username()
        if saved_user:
            self.username_input.setText(saved_user)
            if KEYRING_OK:
                try:
                    saved_pass = keyring.get_password(KEYRING_SERVICE, saved_user)
                    if saved_pass:
                        self.password_input.setText(saved_pass)
                        self.remember_check.setChecked(True)
                except Exception:
                    pass
            self.password_input.setFocus()

        self.remember_check = QCheckBox("مرا به خاطر بسپار (ذخیرهٔ نام کاربری و رمز)")
        if saved_user:
            self.remember_check.setChecked(True)

        form = QFormLayout()
        form.addRow("نام کاربری:", self.username_input)
        form.addRow("رمز عبور:", self.password_input)
        form.addRow("", self.remember_check)

        self.login_btn = QPushButton("ورود")
        self.login_btn.setObjectName("primary")
        self.login_btn.setDefault(True)
        self.login_btn.clicked.connect(self.handle_login)

        settings_btn = QPushButton("تنظیمات اتصال")
        settings_btn.clicked.connect(self.handle_open_settings)

        title = QLabel("سامانه‌ی مدیریت فایل‌های ملکی")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addLayout(form)
        layout.addWidget(self.login_btn)
        layout.addWidget(settings_btn)
        self.setLayout(layout)

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            QMessageBox.warning(self, "خطا", "نام کاربری و رمز عبور را وارد کنید.")
            return
        try:
            api_client.login(username, password)
        except ApiError as e:
            QMessageBox.warning(self, "ورود ناموفق", str(e))
            return

        # --- ذخیره برای دفعات بعد ---
        settings_manager.set_saved_username(username if self.remember_check.isChecked() else "")
        if self.remember_check.isChecked() and KEYRING_OK:
            try:
                keyring.set_password(KEYRING_SERVICE, username, password)
            except Exception:
                pass
        elif not self.remember_check.isChecked() and KEYRING_OK:
            try:
                keyring.delete_password(KEYRING_SERVICE, username)
            except Exception:
                pass

        self.on_success()

    def handle_open_settings(self):
        ConnectionSettingsDialog(self).exec()