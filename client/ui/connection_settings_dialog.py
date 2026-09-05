from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox
)

from api_client import api_client


class ConnectionSettingsDialog(QDialog):
    """
    آدرس سرور دیگر داخل کد هاردکد نیست — این‌جا قابل دیدن/تغییر است و بلافاصله
    (بدون نیاز به بستن و باز کردن مجدد برنامه) در settings.json کنار exe ذخیره
    می‌شود. یعنی اگر IP سرور دفتر عوض شد، دیگر نیازی به تماس با برنامه‌نویس یا
    نصب نسخه‌ی جدید نیست.
    """

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("تنظیمات اتصال به سرور")
        self.resize(420, 180)

        self.server_url_input = QLineEdit(api_client.server_url)
        self.server_url_input.setAlignment(Qt.AlignLeft)  # آدرس همیشه انگلیسی/عددی است

        form = QFormLayout()
        form.addRow("آدرس سرور:", self.server_url_input)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)

        test_btn = QPushButton("تست اتصال")
        test_btn.clicked.connect(self.handle_test_connection)

        save_btn = QPushButton("ذخیره")
        save_btn.clicked.connect(self.handle_save)
        cancel_btn = QPushButton("انصراف")
        cancel_btn.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.addWidget(test_btn)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(QLabel("مثال: http://192.168.1.10:8000 (آدرس سیستم سرور در شبکه‌ی دفتر)"))
        layout.addWidget(self.status_label)
        layout.addLayout(btn_row)
        self.setLayout(layout)

    def handle_test_connection(self):
        url = self.server_url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "خطا", "آدرس سرور را وارد کنید.")
            return
        original_url = api_client.server_url
        api_client.server_url = url.rstrip("/")  # موقتاً برای تست، هنوز ذخیره نشده
        connected = api_client.check_connection()
        api_client.server_url = original_url  # اگر «ذخیره» نزده، تغییر موقت را برگردان

        if connected:
            self.status_label.setText("✅ اتصال برقرار شد")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("❌ اتصال برقرار نشد — آدرس یا شبکه را بررسی کنید")
            self.status_label.setStyleSheet("color: red;")

    def handle_save(self):
        url = self.server_url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "خطا", "آدرس سرور را وارد کنید.")
            return
        api_client.update_server_url(url)
        QMessageBox.information(self, "ذخیره شد", "آدرس سرور ذخیره شد.")
        self.accept()
