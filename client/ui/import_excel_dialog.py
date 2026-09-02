from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog,
    QTextEdit, QMessageBox
)

from api_client import api_client, ApiError


class ImportExcelDialog(QDialog):
    def __init__(self, on_imported):
        super().__init__()
        self.on_imported = on_imported
        self.selected_file_path = None

        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("ایمپورت فایل‌های ملکی از اکسل")
        self.resize(560, 480)

        intro = QLabel(
            "فایل اکسل باید شامل شیت‌های «فروش»، «پیش‌خرید»، «اجاره» و «رهن_کامل» با ستون‌های "
            "استاندارد باشد. اگر قالب را ندارید، ابتدا آن را دانلود و تکمیل کنید."
        )
        intro.setWordWrap(True)

        template_btn = QPushButton("دانلود قالب نمونه‌ی اکسل")
        template_btn.clicked.connect(self.handle_download_template)

        choose_btn = QPushButton("انتخاب فایل اکسل...")
        choose_btn.clicked.connect(self.handle_choose_file)

        self.file_label = QLabel("فایلی انتخاب نشده است.")

        import_btn = QPushButton("شروع Import")
        import_btn.clicked.connect(self.handle_import)

        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.accept)

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setPlaceholderText("گزارش Import پس از اجرا این‌جا نمایش داده می‌شود...")

        top_row = QHBoxLayout()
        top_row.addWidget(template_btn)
        top_row.addWidget(choose_btn)

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(import_btn)
        bottom_row.addWidget(close_btn)

        layout = QVBoxLayout()
        layout.addWidget(intro)
        layout.addLayout(top_row)
        layout.addWidget(self.file_label)
        layout.addWidget(QLabel("گزارش:"))
        layout.addWidget(self.result_box)
        layout.addLayout(bottom_row)
        self.setLayout(layout)

    def handle_download_template(self):
        save_path, _ = QFileDialog.getSaveFileName(
            self, "ذخیره‌ی قالب نمونه", "قالب-ایمپورت-فایل-ملکی.xlsx", "Excel Files (*.xlsx)"
        )
        if not save_path:
            return
        try:
            api_client.download_import_template(save_path)
        except ApiError as e:
            QMessageBox.warning(self, "خطا", str(e))
            return
        QMessageBox.information(self, "موفق", f"قالب نمونه ذخیره شد:\n{save_path}")

    def handle_choose_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "انتخاب فایل اکسل", "", "Excel Files (*.xlsx *.xlsm)")
        if not file_path:
            return
        self.selected_file_path = file_path
        self.file_label.setText(f"فایل انتخاب‌شده: {file_path}")

    def handle_import(self):
        if not self.selected_file_path:
            QMessageBox.warning(self, "توجه", "ابتدا یک فایل اکسل انتخاب کنید.")
            return
        try:
            result = api_client.import_excel(self.selected_file_path)
        except ApiError as e:
            QMessageBox.critical(self, "خطا در Import", str(e))
            return
        except Exception:
            QMessageBox.critical(self, "خطا", "خطا در ارسال فایل به سرور. اتصال شبکه را بررسی کنید.")
            return

        lines = [f"تعداد فایل‌های ثبت‌شده: {result['created']}", f"تعداد ردیف‌های دارای خطا: {result['error_count']}", ""]
        for err in result.get("errors", []):
            lines.append(f"شیت «{err['sheet']}» ردیف {err['row']}: {err['message']}")
        self.result_box.setPlainText("\n".join(lines))

        if result["created"] > 0:
            self.on_imported()
