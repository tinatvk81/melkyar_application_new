from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QVBoxLayout, QLineEdit, QComboBox, QPushButton,
    QHBoxLayout, QMessageBox
)

from api_client import api_client, ApiError

ROLE_LABELS = {"agent": "مشاور", "admin": "مدیر"}


class UserFormDialog(QDialog):
    """ساخت حساب کاربری جدید (مشاور یا مدیر). ویرایش کاربر موجود از این دیالوگ انجام نمی‌شود؛
    برای آن، دکمه‌های جدا (غیرفعال/فعال/ریست رمز) روی هر ردیف در جدول استفاده می‌شود."""

    def __init__(self, on_created):
        super().__init__()
        self.on_created = on_created
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("افزودن حساب کاربری جدید")
        self.resize(360, 260)

        self.username_input = QLineEdit()
        self.full_name_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.role_combo = QComboBox()
        for value, label in ROLE_LABELS.items():
            self.role_combo.addItem(label, value)

        form = QFormLayout()
        form.addRow("نام کاربری:", self.username_input)
        form.addRow("نام و نام‌خانوادگی:", self.full_name_input)
        form.addRow("رمز عبور اولیه:", self.password_input)
        form.addRow("نقش:", self.role_combo)

        save_btn = QPushButton("ساخت حساب")
        save_btn.clicked.connect(self.handle_create)
        cancel_btn = QPushButton("انصراف")
        cancel_btn.clicked.connect(self.reject)
        btn_row = QHBoxLayout()
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(btn_row)
        self.setLayout(layout)

    def handle_create(self):
        username = self.username_input.text().strip()
        full_name = self.full_name_input.text().strip()
        password = self.password_input.text()

        if not username or not full_name or not password:
            QMessageBox.warning(self, "خطا", "همه‌ی فیلدها الزامی است.")
            return
        if len(password) < 6:
            QMessageBox.warning(self, "خطا", "رمز عبور باید حداقل ۶ کاراکتر باشد.")
            return

        try:
            api_client.create_agent(username, full_name, password, self.role_combo.currentData())
        except ApiError as e:
            QMessageBox.critical(self, "خطا", str(e))
            return

        QMessageBox.information(self, "موفق", f"حساب «{username}» با موفقیت ساخته شد.")
        self.on_created()
        self.accept()
