from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QMessageBox, QInputDialog, QLineEdit, QHeaderView, QDialog, QFormLayout,
    QTabWidget, QDoubleSpinBox, QAbstractItemView,
)

from api_client import api_client, ApiError
from session import handle_api_error
from ui.user_form_dialog import UserFormDialog
from ui.property_form import DEAL_TYPE_LABELS

RATE_LABELS = [("sale", "فروش"), ("rent", "اجاره"), ("presale", "پیش‌خرید"), ("mortgage", "رهن کامل")]


class CommissionRatesDialog(QDialog):
    def __init__(self, user, on_saved):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle(f"درصد پورسانت — {user['full_name']}")
        self.user = user
        self.on_saved = on_saved

        current = user.get("commission_rates") or {}
        form = QFormLayout()
        self.spins = {}
        for key, label in RATE_LABELS:
            sp = QDoubleSpinBox()
            sp.setRange(0, 100)
            sp.setDecimals(1)
            sp.setSuffix(" ٪")
            sp.setValue(float(current.get(key) or 0))
            self.spins[key] = sp
            form.addRow(f"{label}:", sp)

        hint = QLabel("این درصد هنگام ثبت معامله به‌صورت پیش‌فرض پیشنهاد می‌شود (قابل تغییر در همان فرم).")
        save_btn = QPushButton("ذخیره")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("انصراف")
        cancel_btn.clicked.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(hint)
        row = QHBoxLayout(); row.addStretch(); row.addWidget(save_btn); row.addWidget(cancel_btn)
        lay.addLayout(row)

    def _save(self):
        rates = {key: sp.value() for key, sp in self.spins.items()}
        try:
            api_client.set_commission_rates(self.user["id"], rates)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.on_saved()
        self.accept()


class AgentDetailDialog(QDialog):
    def __init__(self, user, on_changed):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.user = user
        self.on_changed = on_changed
        self.setWindowTitle(f"پرونده مشاور — {user['full_name']}")
        self.resize(820, 560)

        tabs = QTabWidget()

        # --- مشخصات ---
        info = QWidget()
        form = QFormLayout(info)
        form.addRow("نام کاربری:", QLabel(user["username"]))
        form.addRow("نام کامل:", QLabel(user["full_name"]))
        form.addRow("نقش:", QLabel("مدیر" if user["role"] == "admin" else "مشاور"))
        form.addRow("فعال:", QLabel("بله" if user["is_active"] else "خیر"))
        form.addRow("تلفن:", QLabel(user.get("phone") or "—"))
        rates = user.get("commission_rates") or {}
        rates_txt = " | ".join(
            f"{label}: {rates.get(key, '—')}٪" for key, label in RATE_LABELS
        ) if rates else "تنظیم نشده"
        form.addRow("درصد پورسانت:", QLabel(rates_txt))
        tabs.addTab(info, "مشخصات")

        # --- فایل‌ها ---
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(5)
        self.files_table.setHorizontalHeaderLabels(["#", "شهر", "نوع", "متراژ", "آدرس"])
        self.files_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.files_table.setEditTriggers(QTableWidget.NoEditTriggers)
        tabs.addTab(self.files_table, "فایل‌ها")

        # --- فعالیت‌ها ---
        self.logs_table = QTableWidget()
        self.logs_table.setColumnCount(4)
        self.logs_table.setHorizontalHeaderLabels(["زمان", "عملیات", "نوع", "جزئیات"])
        self.logs_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.logs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        tabs.addTab(self.logs_table, "فعالیت‌ها")

        # --- عملکرد ---
        perf = QWidget()
        perf_form = QFormLayout(perf)
        self.perf_labels = {}
        for key, label in [("total", "تعداد کل فایل"), ("last_30_days", "۳۰ روز اخیر"),
                           ("sale", "فروش"), ("presale", "پیش‌خرید"), ("rent", "اجاره"), ("mortgage", "رهن کامل")]:
            lbl = QLabel("—")
            self.perf_labels[key] = lbl
            form_row = QLabel(label + ":")
            perf_form.addRow(form_row, lbl)
        tabs.addTab(perf, "عملکرد")

        # --- حسابداری ---
        acc = QWidget()
        acc_lay = QFormLayout(acc)
        self.earned_lbl = QLabel("—")
        self.paid_lbl = QLabel("—")
        self.remaining_lbl = QLabel("—")
        acc_lay.addRow("کارکرد (پورسانت قطعی):", self.earned_lbl)
        acc_lay.addRow("پرداخت‌شده:", self.paid_lbl)
        acc_lay.addRow("مانده:", self.remaining_lbl)
        tabs.addTab(acc, "حسابداری")

        lay = QVBoxLayout(self)
        lay.addWidget(tabs)
        self._load_files()
        self._load_logs()
        self._load_performance()
        self._load_balance()

    def _load_files(self):
        try:
            resp = api_client.list_properties(page=1, page_size=200, owner_agent_id=self.user["id"])
            items = resp["items"]
        except ApiError as e:
            handle_api_error(self, e, "خطا در فایل‌ها")
            items = []
        self.files_table.setRowCount(len(items))
        for r, p in enumerate(items):
            self.files_table.setItem(r, 0, QTableWidgetItem(str(p["id"])))
            self.files_table.setItem(r, 1, QTableWidgetItem(p.get("city") or ""))
            self.files_table.setItem(r, 2, QTableWidgetItem(DEAL_TYPE_LABELS.get(p.get("deal_type"), "")))
            self.files_table.setItem(r, 3, QTableWidgetItem(str(p.get("area_m2") or "")))
            self.files_table.setItem(r, 4, QTableWidgetItem(p.get("address") or ""))

    def _load_logs(self):
        try:
            resp = api_client.list_activity_logs(page=1, days=0, user_id=self.user["id"])
            logs = resp["items"]
        except ApiError as e:
            handle_api_error(self, e, "خطا در فعالیت‌ها")
            logs = []
        self.logs_table.setRowCount(len(logs))
        for r, log in enumerate(logs):
            self.logs_table.setItem(r, 0, QTableWidgetItem(log["created_at"].replace("T", " ")[:16]))
            self.logs_table.setItem(r, 1, QTableWidgetItem(log.get("action") or ""))
            self.logs_table.setItem(r, 2, QTableWidgetItem(log.get("entity_type") or ""))
            self.logs_table.setItem(r, 3, QTableWidgetItem(log.get("detail") or ""))

    def _load_performance(self):
        try:
            agents = api_client.get_agent_performance()
        except ApiError:
            return
        mine = next((a for a in agents if a["user_id"] == self.user["id"]), None)
        if not mine:
            return
        self.perf_labels["total"].setText(str(mine.get("total", 0)))
        self.perf_labels["last_30_days"].setText(str(mine.get("last_30_days", 0)))
        by = mine.get("by_deal_type", {})
        for key in ("sale", "presale", "rent", "mortgage"):
            self.perf_labels[key].setText(str(by.get(key, 0)))

    def _load_balance(self):
        try:
            rows = api_client.get_balances()
        except ApiError:
            return
        mine = next((b for b in rows if b["user_id"] == self.user["id"]), None)
        if not mine:
            return
        self.earned_lbl.setText(f"{mine['earned']:,} تومان")
        self.paid_lbl.setText(f"{mine['paid']:,} تومان")
        self.remaining_lbl.setText(f"{mine['remaining']:,} تومان")

class AgentCenterTab(QWidget):
    """مرکز مدیریت مشاوران: جدول کاربران + پروندهٔ کامل با دابل‌کلیک."""

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._users_by_row = []

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["نام کاربری", "نام کامل", "نقش", "فعال", "تلفن", "درصد پورسانت"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.doubleClicked.connect(self._open_detail)

        add_btn = QPushButton("افزودن حساب جدید")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self.handle_add_new)

        self.activate_btn = QPushButton("فعال‌سازی حساب")
        self.activate_btn.clicked.connect(self.handle_activate)

        self.deactivate_btn = QPushButton("غیرفعال‌سازی حساب")
        self.deactivate_btn.clicked.connect(self.handle_deactivate)

        reset_pw_btn = QPushButton("ریست رمز عبور")
        reset_pw_btn.clicked.connect(self.handle_reset_password)
        edit_phone_btn = QPushButton("ویرایش تلفن")
        edit_phone_btn.clicked.connect(self.handle_edit_phone)
        rates_btn = QPushButton("درصد پورسانت")
        rates_btn.clicked.connect(self.handle_set_rates)
        refresh_btn = QPushButton("به‌روزرسانی")
        refresh_btn.clicked.connect(self.load_users)

        # فعال/غیرفعال شدن دکمه‌ها بر اساس انتخاب فعلی
        self.table.itemSelectionChanged.connect(self._update_buttons)

        bar = QHBoxLayout()
        bar.addWidget(add_btn)
        bar.addWidget(self.activate_btn)
        bar.addWidget(self.deactivate_btn)
        bar.addWidget(reset_pw_btn)
        bar.addWidget(edit_phone_btn)
        bar.addWidget(rates_btn)
        bar.addStretch()
        bar.addWidget(refresh_btn)

        lay = QVBoxLayout(self)
        lay.addLayout(bar)
        lay.addWidget(self.table)
        self.load_users()

    def load_users(self):
        try:
            users = api_client.list_users()
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self._users_by_row = users
        self.table.setRowCount(len(users))
        for r, u in enumerate(users):
            rates = u.get("commission_rates") or {}
            rates_txt = " | ".join(f"{lbl} {rates.get(k, 0):g}٪" for k, lbl in RATE_LABELS) if rates else "—"
            self.table.setItem(r, 0, QTableWidgetItem(u["username"]))
            self.table.setItem(r, 1, QTableWidgetItem(u["full_name"]))
            self.table.setItem(r, 2, QTableWidgetItem("مدیر" if u["role"] == "admin" else "مشاور"))
            self.table.setItem(r, 3, QTableWidgetItem("بله" if u["is_active"] else "خیر"))
            self.table.setItem(r, 4, QTableWidgetItem(u.get("phone") or ""))
            self.table.setItem(r, 5, QTableWidgetItem(rates_txt))
        self._update_buttons()

    def _selected_user(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._users_by_row):
            return None
        return self._users_by_row[row]

    def _open_detail(self):
        u = self._selected_user()
        if not u:
            return
        AgentDetailDialog(u, on_changed=self.load_users).exec()

    def handle_add_new(self):
        UserFormDialog(on_created=self.load_users).exec()

    def _update_buttons(self):
        u = self._selected_user()
        self.activate_btn.setEnabled(bool(u) and not u["is_active"])
        self.deactivate_btn.setEnabled(bool(u) and u["is_active"])

    def handle_activate(self):
        u = self._selected_user()
        if u:
            try:
                api_client.activate_user(u["id"])
            except ApiError as e:
                handle_api_error(self, e, "خطا")
                return
            self.load_users()

    def handle_deactivate(self):
        u = self._selected_user()
        if not u:
            return
        if QMessageBox.question(self, "تایید", f"حساب «{u['username']}» غیرفعال شود؟") != QMessageBox.Yes:
            return
        try:
            api_client.deactivate_user(u["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.load_users()

    def handle_reset_password(self):
        u = self._selected_user()
        if not u:
            QMessageBox.information(self, "توجه", "ابتدا یک کاربر را انتخاب کنید.")
            return
        pw, ok = QInputDialog.getText(self, "ریست رمز عبور", f"رمز جدید برای «{u['username']}»:", QLineEdit.Password)
        if not ok or not pw:
            return
        if len(pw) < 6:
            QMessageBox.warning(self, "خطا", "رمز باید حداقل ۶ کاراکتر باشد.")
            return
        try:
            api_client.reset_user_password(u["id"], pw)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        QMessageBox.information(self, "موفق", "رمز تغییر کرد؛ به‌صورت امن اطلاع دهید.")

    def handle_edit_phone(self):
        u = self._selected_user()
        if not u:
            QMessageBox.information(self, "توجه", "ابتدا یک کاربر را انتخاب کنید.")
            return
        phone, ok = QInputDialog.getText(self, "ویرایش تلفن", "تلفن همراه:", text=u.get("phone") or "")
        if not ok:
            return
        try:
            api_client.update_user_phone(u["id"], phone.strip())
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.load_users()

    def handle_set_rates(self):
        u = self._selected_user()
        if not u:
            QMessageBox.information(self, "توجه", "ابتدا یک کاربر را انتخاب کنید.")
            return
        CommissionRatesDialog(u, on_saved=self.load_users).exec()
