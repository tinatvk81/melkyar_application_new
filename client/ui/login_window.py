from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QLabel, QMessageBox
)

from api_client import api_client, ApiError
from ui.connection_settings_dialog import ConnectionSettingsDialog


class LoginWindow(QWidget):
    def __init__(self, on_success):
        super().__init__()
        self.on_success = on_success
        self.setWindowTitle("ورود به سامانه‌ی مدیریت فایل‌های ملکی")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(380, 260)

        self.username_input = QLineEdit()
        self.username_input.setAlignment(Qt.AlignRight)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setAlignment(Qt.AlignRight)
        self.password_input.returnPressed.connect(self.handle_login)

        form = QFormLayout()
        form.addRow("نام کاربری:", self.username_input)
        form.addRow("رمز عبور:", self.password_input)

        login_btn = QPushButton("ورود")
        login_btn.clicked.connect(self.handle_login)

        settings_btn = QPushButton("تنظیمات اتصال")
        settings_btn.clicked.connect(self.handle_open_settings)

        title = QLabel("سامانه‌ی مدیریت فایل‌های ملکی")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addLayout(form)
        layout.addWidget(login_btn)
        layout.addWidget(settings_btn)
        self.setLayout(layout)

    def handle_open_settings(self):
        dialog = ConnectionSettingsDialog()
        dialog.exec()

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            QMessageBox.warning(self, "خطا", "لطفاً نام کاربری و رمز عبور را وارد کنید.")
            return
        try:
            api_client.login(username, password)
        except ApiError as e:
            QMessageBox.critical(self, "ورود ناموفق", str(e))
            return
        except Exception:
            QMessageBox.critical(
                self, "خطای اتصال",
                "اتصال به سرور برقرار نشد. آدرس سرور را از دکمه‌ی «تنظیمات اتصال» بررسی کنید."
            )
            return

        self.on_success()
