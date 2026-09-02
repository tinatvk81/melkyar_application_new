from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QHBoxLayout, QMessageBox, QInputDialog, QLineEdit,
    QFileDialog
)

from api_client import api_client, ApiError
from ui.property_form import PropertyFormDialog, DEAL_TYPE_LABELS
from ui.import_excel_dialog import ImportExcelDialog
from ui.user_form_dialog import UserFormDialog, ROLE_LABELS
from ui.property_filter_panel import PropertyFilterPanel


class PropertyListTab(QWidget):
    """فهرست فایل‌ها — برای مشاور فقط فایل‌های خودش، برای مدیر همه (فیلتر در سرور اعمال می‌شود)."""

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._properties_by_row = []  # برای پیدا کردن دیتای کامل هنگام دابل‌کلیک برای ویرایش
        self._current_filters = {}  # آخرین فیلتری که اعمال شده (برای استفاده در export هم)
        self._current_page = 1
        self._total_pages = 1

        self.filter_panel = PropertyFilterPanel(on_apply=self._handle_apply_filters, on_clear=self._handle_clear_filters)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["شهر", "نوع معامله", "متراژ", "اتاق", "آدرس", "تاریخ پایان قرارداد"]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.doubleClicked.connect(self.handle_edit_selected)

        add_btn = QPushButton("افزودن فایل جدید")
        add_btn.clicked.connect(self.handle_add_new)

        edit_btn = QPushButton("ویرایش فایل انتخاب‌شده")
        edit_btn.clicked.connect(self.handle_edit_selected)

        deactivate_btn = QPushButton("غیرفعال کردن فایل انتخاب‌شده")
        deactivate_btn.clicked.connect(self.handle_deactivate_selected)

        import_btn = QPushButton("ایمپورت از اکسل")
        import_btn.clicked.connect(self.handle_import_excel)

        export_pdf_btn = QPushButton("خروجی PDF")
        export_pdf_btn.clicked.connect(self.handle_export_pdf)

        export_excel_btn = QPushButton("خروجی اکسل")
        export_excel_btn.clicked.connect(self.handle_export_excel)

        refresh_btn = QPushButton("به‌روزرسانی فهرست")
        refresh_btn.clicked.connect(self.load_properties)

        top_bar = QHBoxLayout()
        top_bar.addWidget(add_btn)
        top_bar.addWidget(edit_btn)
        top_bar.addWidget(deactivate_btn)
        top_bar.addWidget(import_btn)
        top_bar.addWidget(export_pdf_btn)
        top_bar.addWidget(export_excel_btn)
        top_bar.addStretch()
        top_bar.addWidget(refresh_btn)

        # --- نوار صفحه‌بندی: بدون این، فایل‌های بعد از یک تعداد مشخص بی‌صدا از دید پنهان می‌ماندند ---
        self.prev_page_btn = QPushButton("◀ صفحه‌ی قبل")
        self.prev_page_btn.clicked.connect(self.handle_prev_page)
        self.next_page_btn = QPushButton("صفحه‌ی بعد ▶")
        self.next_page_btn.clicked.connect(self.handle_next_page)
        self.page_status_label = QLabel("")
        self.page_status_label.setAlignment(Qt.AlignCenter)

        pagination_bar = QHBoxLayout()
        pagination_bar.addWidget(self.prev_page_btn)
        pagination_bar.addStretch()
        pagination_bar.addWidget(self.page_status_label)
        pagination_bar.addStretch()
        pagination_bar.addWidget(self.next_page_btn)

        layout = QVBoxLayout()
        layout.addWidget(self.filter_panel)
        layout.addLayout(top_bar)
        layout.addWidget(self.table)
        layout.addLayout(pagination_bar)
        self.setLayout(layout)

        self.load_properties()

    def _handle_apply_filters(self, filters: dict):
        self._current_filters = filters
        self._current_page = 1
        self.load_properties()

    def _handle_clear_filters(self):
        self._current_filters = {}
        self._current_page = 1
        self.load_properties()

    def handle_prev_page(self):
        if self._current_page > 1:
            self._current_page -= 1
            self.load_properties()

    def handle_next_page(self):
        if self._current_page < self._total_pages:
            self._current_page += 1
            self.load_properties()

    def load_properties(self):
        try:
            response = api_client.list_properties(page=self._current_page, **self._current_filters)
        except ApiError as e:
            QMessageBox.warning(self, "خطا", str(e))
            return

        properties = response["items"]
        self._total_pages = response["total_pages"]
        # اگر با تغییر فیلتر صفحه‌ی فعلی از تعداد صفحات جدید بیشتر شد، به آخرین صفحه‌ی معتبر برگرد
        if self._current_page > self._total_pages:
            self._current_page = self._total_pages
            if properties == [] and self._total_pages >= 1:
                self.load_properties()
                return

        self.page_status_label.setText(
            f"صفحه {self._current_page} از {self._total_pages} — تعداد کل: {response['total']}"
        )
        self.prev_page_btn.setEnabled(self._current_page > 1)
        self.next_page_btn.setEnabled(self._current_page < self._total_pages)

        self._properties_by_row = properties
        self.table.setRowCount(len(properties))
        for row, p in enumerate(properties):
            self.table.setItem(row, 0, QTableWidgetItem(p.get("city", "")))
            self.table.setItem(row, 1, QTableWidgetItem(DEAL_TYPE_LABELS.get(p.get("deal_type"), p.get("deal_type", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(str(p.get("area_m2") or "")))
            self.table.setItem(row, 3, QTableWidgetItem(str(p.get("rooms") or "")))
            self.table.setItem(row, 4, QTableWidgetItem(p.get("address") or ""))
            self.table.setItem(row, 5, QTableWidgetItem(p.get("contract_end_date") or ""))

    def _selected_property(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._properties_by_row):
            return None
        return self._properties_by_row[row]

    def handle_add_new(self):
        dialog = PropertyFormDialog(property_data=None, on_saved=self.load_properties)
        dialog.exec()

    def handle_edit_selected(self):
        prop = self._selected_property()
        if not prop:
            QMessageBox.information(self, "توجه", "ابتدا یک فایل را از فهرست انتخاب کنید.")
            return
        dialog = PropertyFormDialog(property_data=prop, on_saved=self.load_properties)
        dialog.exec()

    def handle_deactivate_selected(self):
        prop = self._selected_property()
        if not prop:
            QMessageBox.information(self, "توجه", "ابتدا یک فایل را از فهرست انتخاب کنید.")
            return
        confirm = QMessageBox.question(
            self, "تایید", f"فایل «{prop.get('address') or prop.get('city')}» غیرفعال شود؟"
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            api_client.deactivate_property(prop["id"])
        except ApiError as e:
            QMessageBox.warning(self, "خطا", str(e))
            return
        self.load_properties()

    def handle_import_excel(self):
        dialog = ImportExcelDialog(on_imported=self.load_properties)
        dialog.exec()

    def handle_export_pdf(self):
        save_path, _ = QFileDialog.getSaveFileName(self, "ذخیره‌ی PDF", "فهرست-فایل-ها.pdf", "PDF Files (*.pdf)")
        if not save_path:
            return
        try:
            api_client.export_properties_pdf(save_path, **self._current_filters)
        except ApiError as e:
            QMessageBox.warning(self, "خطا", str(e))
            return
        QMessageBox.information(self, "موفق", f"فایل PDF ذخیره شد:\n{save_path}")

    def handle_export_excel(self):
        save_path, _ = QFileDialog.getSaveFileName(
            self, "ذخیره‌ی اکسل", "فهرست-فایل-ها.xlsx", "Excel Files (*.xlsx)"
        )
        if not save_path:
            return
        try:
            api_client.export_properties_excel(save_path, **self._current_filters)
        except ApiError as e:
            QMessageBox.warning(self, "خطا", str(e))
            return
        QMessageBox.information(self, "موفق", f"فایل اکسل ذخیره شد:\n{save_path}")


class RenewalsTab(QWidget):
    """قراردادهای رو‌به‌اتمام (ماژول یادآوری)."""

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["شهر", "آدرس", "تاریخ پایان قرارداد", "تلفن مالک"])

        refresh_btn = QPushButton("به‌روزرسانی")
        refresh_btn.clicked.connect(self.load_renewals)

        layout = QVBoxLayout()
        layout.addWidget(refresh_btn)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.load_renewals()

    def load_renewals(self):
        try:
            items = api_client.upcoming_renewals(days=30)
        except ApiError as e:
            QMessageBox.warning(self, "خطا", str(e))
            return
        self.table.setRowCount(len(items))
        for row, p in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(p.get("city", "")))
            self.table.setItem(row, 1, QTableWidgetItem(p.get("address") or ""))
            self.table.setItem(row, 2, QTableWidgetItem(p.get("contract_end_date") or ""))
            self.table.setItem(row, 3, QTableWidgetItem(p.get("owner_phone") or ""))


class UserManagementTab(QWidget):
    """فقط برای مدیر: مدیریت حساب مشاوران."""

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._users_by_row = []

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["نام کاربری", "نام کامل", "نقش", "فعال"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        add_btn = QPushButton("افزودن حساب جدید")
        add_btn.clicked.connect(self.handle_add_new)

        self.toggle_btn = QPushButton("غیرفعال‌سازی حساب انتخاب‌شده")
        self.toggle_btn.clicked.connect(self.handle_toggle_active)

        reset_pw_btn = QPushButton("ریست رمز عبور حساب انتخاب‌شده")
        reset_pw_btn.clicked.connect(self.handle_reset_password)

        refresh_btn = QPushButton("به‌روزرسانی فهرست کاربران")
        refresh_btn.clicked.connect(self.load_users)

        self.table.itemSelectionChanged.connect(self._update_toggle_button_label)

        top_bar = QHBoxLayout()
        top_bar.addWidget(add_btn)
        top_bar.addWidget(self.toggle_btn)
        top_bar.addWidget(reset_pw_btn)
        top_bar.addStretch()
        top_bar.addWidget(refresh_btn)

        layout = QVBoxLayout()
        layout.addLayout(top_bar)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.load_users()

    def load_users(self):
        try:
            users = api_client.list_users()
        except ApiError as e:
            QMessageBox.warning(self, "خطا", str(e))
            return
        self._users_by_row = users
        self.table.setRowCount(len(users))
        for row, u in enumerate(users):
            self.table.setItem(row, 0, QTableWidgetItem(u["username"]))
            self.table.setItem(row, 1, QTableWidgetItem(u["full_name"]))
            self.table.setItem(row, 2, QTableWidgetItem(ROLE_LABELS.get(u["role"], u["role"])))
            self.table.setItem(row, 3, QTableWidgetItem("بله" if u["is_active"] else "خیر"))
        self._update_toggle_button_label()

    def _selected_user(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._users_by_row):
            return None
        return self._users_by_row[row]

    def _update_toggle_button_label(self):
        user = self._selected_user()
        if user and not user["is_active"]:
            self.toggle_btn.setText("فعال‌سازی حساب انتخاب‌شده")
        else:
            self.toggle_btn.setText("غیرفعال‌سازی حساب انتخاب‌شده")

    def handle_add_new(self):
        dialog = UserFormDialog(on_created=self.load_users)
        dialog.exec()

    def handle_toggle_active(self):
        user = self._selected_user()
        if not user:
            QMessageBox.information(self, "توجه", "ابتدا یک کاربر را از فهرست انتخاب کنید.")
            return

        if user["is_active"]:
            confirm = QMessageBox.question(
                self, "تایید",
                f"حساب «{user['username']}» غیرفعال شود؟ او دیگر نمی‌تواند وارد شود و نشست فعلی‌اش هم فوراً بسته می‌شود."
            )
            if confirm != QMessageBox.Yes:
                return
            action = api_client.deactivate_user
        else:
            action = api_client.activate_user

        try:
            action(user["id"])
        except ApiError as e:
            QMessageBox.warning(self, "خطا", str(e))
            return
        self.load_users()

    def handle_reset_password(self):
        user = self._selected_user()
        if not user:
            QMessageBox.information(self, "توجه", "ابتدا یک کاربر را از فهرست انتخاب کنید.")
            return

        new_password, ok = QInputDialog.getText(
            self, "ریست رمز عبور", f"رمز عبور جدید برای «{user['username']}»:", QLineEdit.Password
        )
        if not ok or not new_password:
            return
        if len(new_password) < 6:
            QMessageBox.warning(self, "خطا", "رمز عبور باید حداقل ۶ کاراکتر باشد.")
            return

        try:
            api_client.reset_user_password(user["id"], new_password)
        except ApiError as e:
            QMessageBox.warning(self, "خطا", str(e))
            return
        QMessageBox.information(
            self, "موفق",
            f"رمز عبور «{user['username']}» تغییر کرد. این رمز جدید را حتماً به‌صورت امن به او اطلاع دهید."
        )


class AgentPerformanceTab(QWidget):
    """فقط برای مدیر: گزارش عملکرد مشاوران (تعداد فایل به تفکیک نوع معامله)."""

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["نام مشاور", "تعداد کل فایل", "۳۰ روز اخیر", "فروش", "پیش‌خرید", "اجاره", "رهن کامل"]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        refresh_btn = QPushButton("به‌روزرسانی گزارش")
        refresh_btn.clicked.connect(self.load_report)

        export_btn = QPushButton("خروجی PDF گزارش")
        export_btn.clicked.connect(self.handle_export_pdf)

        top_bar = QHBoxLayout()
        top_bar.addWidget(refresh_btn)
        top_bar.addWidget(export_btn)
        top_bar.addStretch()

        layout = QVBoxLayout()
        layout.addLayout(top_bar)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.load_report()

    def load_report(self):
        try:
            agents = api_client.get_agent_performance()
        except ApiError as e:
            QMessageBox.warning(self, "خطا", str(e))
            return

        self.table.setRowCount(len(agents))
        for row, agent in enumerate(agents):
            by_type = agent.get("by_deal_type", {})
            self.table.setItem(row, 0, QTableWidgetItem(agent.get("full_name") or agent.get("username") or ""))
            self.table.setItem(row, 1, QTableWidgetItem(str(agent.get("total", 0))))
            self.table.setItem(row, 2, QTableWidgetItem(str(agent.get("last_30_days", 0))))
            self.table.setItem(row, 3, QTableWidgetItem(str(by_type.get("sale", 0))))
            self.table.setItem(row, 4, QTableWidgetItem(str(by_type.get("presale", 0))))
            self.table.setItem(row, 5, QTableWidgetItem(str(by_type.get("rent", 0))))
            self.table.setItem(row, 6, QTableWidgetItem(str(by_type.get("mortgage", 0))))

    def handle_export_pdf(self):
        save_path, _ = QFileDialog.getSaveFileName(
            self, "ذخیره‌ی گزارش PDF", "گزارش-عملکرد-مشاوران.pdf", "PDF Files (*.pdf)"
        )
        if not save_path:
            return
        try:
            api_client.export_agent_performance_pdf(save_path)
        except ApiError as e:
            QMessageBox.warning(self, "خطا", str(e))
            return
        QMessageBox.information(self, "موفق", f"گزارش ذخیره شد:\n{save_path}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle(f"سامانه‌ی مدیریت فایل‌های ملکی — {api_client.full_name}")
        self.resize(1000, 650)

        tabs = QTabWidget()
        tabs.addTab(PropertyListTab(), "فهرست فایل‌ها")
        tabs.addTab(RenewalsTab(), "قراردادهای رو‌به‌اتمام")

        if api_client.role == "admin":
            tabs.addTab(AgentPerformanceTab(), "گزارش عملکرد مشاوران")
            tabs.addTab(UserManagementTab(), "مدیریت کاربران")

        self.setCentralWidget(tabs)
