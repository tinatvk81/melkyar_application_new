from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QMessageBox, QInputDialog, QLineEdit, QHeaderView, QDialog, QFormLayout,
    QTabWidget, QDoubleSpinBox, QAbstractItemView,
)
from PySide6.QtGui import QColor

from ui.spinner import TableSpinner
from api_client import api_client, ApiError
from session import handle_api_error
from ui.user_form_dialog import UserFormDialog
from ui.property_form import DEAL_TYPE_LABELS
from ui.widgets import AVATAR_COLORS
from ui.jalali_util import to_jalali_str

RATE_LABELS = [("sale", "فروش"), ("rent", "اجاره"), ("presale", "پیش‌خرید"), ("mortgage", "رهن کامل")]


def _avatar_item(name: str) -> QTableWidgetItem:
    letter = (name or "?").strip()[:1].upper() or "?"
    color = AVATAR_COLORS[(len(name or "x")) % len(AVATAR_COLORS)]
    it = QTableWidgetItem(f"{letter}  {name}")
    it.setForeground(QColor(color))
    f = it.font(); f.setBold(True); it.setFont(f)
    return it


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
        role_item = QLabel("● مدیر" if user["role"] == "admin" else "● مشاور")
        role_item.setStyleSheet(
            f"color: {'#f5a623' if user['role'] == 'admin' else '#7dd3fc'}; font-weight: bold;")
        active_item = QLabel("● فعال" if user["is_active"] else "● غیرفعال")
        active_item.setStyleSheet(
            f"color: {'#22c55e' if user['is_active'] else '#ef4444'}; font-weight: bold;")
        form.addRow("نام کاربری:", QLabel(user["username"]))
        form.addRow("نام کامل:", QLabel(user["full_name"]))
        form.addRow("نقش:", role_item)
        form.addRow("وضعیت:", active_item)
        form.addRow("تلفن:", QLabel(user.get("phone") or "—"))
        rates = user.get("commission_rates") or {}
        rates_txt = " | ".join(f"{label}: {rates.get(key, '—')}٪" for key, label in RATE_LABELS) if rates else "تنظیم نشده"
        form.addRow("درصد پورسانت:", QLabel(rates_txt))
        tabs.addTab(info, "مشخصات")

        # --- فایل‌ها ---
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(6)
        self.files_table.setHorizontalHeaderLabels(["فایل", "شهر", "نوع", "متراژ", "قیمت", "آدرس"])
        self.files_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
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
            perf_form.addRow(QLabel(label + ":"), lbl)
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
            chip = QTableWidgetItem(f"🔖 MLK-{p['id']:04d}")
            chip.setForeground(QColor("#7dd3fc"))
            _cf = chip.font(); _cf.setBold(True); chip.setFont(_cf)
            self.files_table.setItem(r, 0, chip)
            self.files_table.setItem(r, 1, QTableWidgetItem(p.get("city") or ""))
            self.files_table.setItem(r, 2, QTableWidgetItem(DEAL_TYPE_LABELS.get(p.get("deal_type"), "")))
            _a = p.get("area_m2")
            self.files_table.setItem(r, 3, QTableWidgetItem(f"{_a:g}" if _a else "—"))
            self.files_table.setItem(r, 4, QTableWidgetItem(p.get("price_display") or "—"))
            self.files_table.setItem(r, 5, QTableWidgetItem(p.get("address") or ""))

    def _load_logs(self):
        try:
            resp = api_client.list_activity_logs(page=1, days=0, user_id=self.user["id"])
            logs = resp["items"]
        except ApiError as e:
            handle_api_error(self, e, "خطا در فعالیت‌ها")
            logs = []
        self.logs_table.setRowCount(len(logs))
        for r, log in enumerate(logs):
            self.logs_table.setItem(r, 0, QTableWidgetItem(to_jalali_str(log["created_at"], with_time=True)))
            act = log.get("action") or ""
            it = QTableWidgetItem(f"● {act}")
            it.setForeground(QColor({"create": "#22c55e", "login": "#7dd3fc",
                                     "update": "#f5a623", "delete": "#ef4444"}.get(act, "#a5b4fc")))
            self.logs_table.setItem(r, 1, it)
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
    """مرکز مدیریت مشاوران — نوار آمار + آواتار رنگی + بج نقش/وضعیت."""

    ROLE_FA = {"admin": "مدیر", "agent": "مشاور"}

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._users_by_row = []

        # --- نوار عنوان + چیپ‌های آماری ---
        title_row = QHBoxLayout()
        ttl = QLabel("👥 مشاوران و مدیریت")
        ttl.setStyleSheet("font-size: 15px; font-weight: 800; color: #f5a623; background: transparent;")
        title_row.addWidget(ttl)
        title_row.addSpacing(18)
        self._stat_chips = {}
        for key, label, color in [("total", "کل کاربران", "#f5a623"), ("admin", "مدیر", "#c4b5fd"),
                                  ("agent", "مشاور", "#7dd3fc"), ("inactive", "غیرفعال", "#ef4444")]:
            chip = QLabel(f"{label}: 0")
            chip.setStyleSheet(
                f"color: {color}; background: rgba(255,255,255,0.05);"
                f"border: 1px solid {color}55; border-radius: 12px;"
                "padding: 4px 12px; font-size: 11px; font-weight: bold;")
            self._stat_chips[key] = chip
            title_row.addWidget(chip)
        title_row.addStretch()

        # --- جدول ---
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["کاربر", "نام کاربری", "نقش", "وضعیت", "تلفن", "درصد پورسانت", "فایل‌ها"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._open_detail)

        add_btn = QPushButton("➕ افزودن حساب جدید")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self.handle_add_new)

        self.activate_btn = QPushButton("✅ فعال‌سازی")
        self.activate_btn.clicked.connect(self.handle_activate)

        self.deactivate_btn = QPushButton("⛔ غیرفعال‌سازی")
        self.deactivate_btn.setStyleSheet(
            "QPushButton { color: #f87171; border-color: rgba(239,68,68,0.45); }"
            "QPushButton:hover { background: rgba(239,68,68,0.15); border-color: #ef4444; }")
        self.deactivate_btn.clicked.connect(self.handle_deactivate)

        reset_pw_btn = QPushButton("🔑 ریست رمز")
        reset_pw_btn.clicked.connect(self.handle_reset_password)
        edit_phone_btn = QPushButton("📞 ویرایش تلفن")
        edit_phone_btn.clicked.connect(self.handle_edit_phone)
        rates_btn = QPushButton("٪ درصد پورسانت")
        rates_btn.clicked.connect(self.handle_set_rates)
        refresh_btn = QPushButton("🔄 به‌روزرسانی")
        refresh_btn.clicked.connect(self.load_users)

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
        lay.addLayout(title_row)
        lay.addSpacing(4)
        lay.addLayout(bar)
        lay.addWidget(self.table)
        self.load_users()

    def load_users(self):
        TableSpinner.show(self.table)
        try:
            users = api_client.list_users()
        except ApiError as e:
            TableSpinner.hide(self.table)
            handle_api_error(self, e, "خطا")
            return
        TableSpinner.hide(self.table)

        self._users_by_row = users
        counts = {"total": len(users), "admin": 0, "agent": 0, "inactive": 0}
        for u in users:
            counts["admin" if u["role"] == "admin" else "agent"] += 1
            if not u.get("is_active"):
                counts["inactive"] += 1
        for key, chip in self._stat_chips.items():
            chip.setText(chip.text().split(":")[0] + f": {counts.get(key, 0)}")

        self.table.setRowCount(len(users))
        for r, u in enumerate(users):
            # آواتار رنگی + نام کامل
            self.table.setItem(r, 0, _avatar_item(u["full_name"]))
            self.table.setItem(r, 1, QTableWidgetItem(u["username"]))

            role = u["role"]
            role_item = QTableWidgetItem(f"● {self.ROLE_FA.get(role, role)}")
            role_item.setForeground(QColor("#f5a623" if role == "admin" else "#7dd3fc"))
            _rf = role_item.font(); _rf.setBold(True); role_item.setFont(_rf)
            self.table.setItem(r, 2, role_item)

            st_item = QTableWidgetItem("● فعال" if u["is_active"] else "● غیرفعال")
            st_item.setForeground(QColor("#22c55e" if u["is_active"] else "#ef4444"))
            self.table.setItem(r, 3, st_item)

            self.table.setItem(r, 4, QTableWidgetItem(u.get("phone") or ""))
            rates = u.get("commission_rates") or {}
            rates_txt = " | ".join(f"{lbl} {rates.get(k, 0):g}٪" for k, lbl in RATE_LABELS) if rates else "—"
            self.table.setItem(r, 5, QTableWidgetItem(rates_txt))
            self.table.setItem(r, 6, QTableWidgetItem(str(u.get("files_count", "—"))))
        self._update_buttons()

    def _selected_user(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._users_by_row):
            return None
        return self._users_by_row[row]

    def _open_detail(self):
        u = self._selected_user()
        if u:
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