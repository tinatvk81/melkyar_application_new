from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QComboBox, QMessageBox, QDialog, QFormLayout, QLineEdit, QTextEdit,
    QHeaderView, QAbstractItemView, QTimeEdit, QCheckBox,
)

from api_client import api_client, ApiError
from session import handle_api_error
from ui.jalali_date_edit import JalaliDateEdit
from ui.property_form import PropertyFormDialog

STATUS_FA = {"pending": "در انتظار", "done": "انجام شد", "canceled": "لغو"}


class FollowUpDialog(QDialog):
    def __init__(self, data=None, on_saved=None):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.data = data
        self.on_saved = on_saved
        self.setWindowTitle("ویرایش پیگیری" if data else "پیگیری جدید")
        self.resize(460, 440)

        form = QFormLayout()
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("مثلاً: تماس با مالک پونک برای هماهنگی بازدید")
        self.desc_input = QTextEdit(); self.desc_input.setFixedHeight(70)
        self.date_input = JalaliDateEdit(allow_empty=True)

        self.time_check = QCheckBox("تعیین ساعت")
        self.time_edit = QTimeEdit(QTime(9, 0))
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setEnabled(False)
        self.time_edit.setMinimumWidth(110)
        self.time_check.toggled.connect(self.time_edit.setEnabled)
        time_row = QHBoxLayout()
        time_row.addWidget(self.time_check)
        time_row.addWidget(self.time_edit)
        
        time_wrap = QWidget(); time_wrap.setLayout(time_row)

        self.prop_combo = QComboBox()
        self.prop_combo.addItem("— بدون ارتباط با فایل —", None)
        try:
            props = api_client.list_properties(page=1, page_size=200)["items"]
            for p in props:
                self.prop_combo.addItem(f"#{p['id']} — {p.get('city','')} — {p.get('address') or ''}", p["id"])
        except ApiError:
            pass

        form.addRow("عنوان *:", self.title_input)
        form.addRow("توضیحات:", self.desc_input)
        form.addRow("سررسید:", self.date_input)
        form.addRow("ساعت:", time_wrap)
        form.addRow("فایل مرتبط:", self.prop_combo)

        if data:
            self.title_input.setText(data.get("title") or "")
            self.desc_input.setPlainText(data.get("description") or "")
            if data.get("due_date"):
                from datetime import date as _d
                self.date_input.set_gregorian_date(_d.fromisoformat(data["due_date"]))
            if data.get("due_time"):
                self.time_check.setChecked(True)
                t = QTime.fromString(data["due_time"], "HH:mm")
                if t.isValid():
                    self.time_edit.setTime(t)
            if data.get("property_id"):
                idx = self.prop_combo.findData(data["property_id"])
                self.prop_combo.setCurrentIndex(max(idx, 0))

        save_btn = QPushButton("ذخیره"); save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("انصراف"); cancel_btn.clicked.connect(self.reject)
        row = QHBoxLayout(); row.addStretch(); row.addWidget(save_btn); row.addWidget(cancel_btn)

        lay = QVBoxLayout(self); lay.addLayout(form); lay.addLayout(row)

    def _save(self):
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "خطا", "عنوان الزامی است.")
            return
        payload = {
            "title": title,
            "description": self.desc_input.toPlainText().strip() or None,
            "due_date": self.date_input.get_iso_string(),
            "due_time": self.time_edit.time().toString("HH:mm") if self.time_check.isChecked() else None,
            "property_id": self.prop_combo.currentData(),
        }
        try:
            if self.data:
                api_client.update_follow_up(self.data["id"], payload)
            else:
                api_client.create_follow_up(payload)
        except ApiError as e:
            handle_api_error(self, e, "خطا در ذخیره پیگیری")
            return
        if self.on_saved:
            self.on_saved()
        self.accept()


class NotificationsDialog(QDialog):
    def __init__(self, on_changed=None):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.on_changed = on_changed
        self.setWindowTitle("اطلاع‌یه‌ها")
        self.resize(620, 470)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["اطلاع‌یه", "زمان", "وضعیت"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.doubleClicked.connect(self._mark_one)
        self.table.itemSelectionChanged.connect(self._update_exp_buttons)

        read_btn = QPushButton("خواندم (انتخاب‌شده)")
        read_btn.clicked.connect(self._mark_one)
        all_btn = QPushButton("همه خوانده شد")
        all_btn.setObjectName("primary")
        all_btn.clicked.connect(self._mark_all)
        close_btn = QPushButton("بستن"); close_btn.clicked.connect(self.accept)

        self.exp_confirm_btn = QPushButton("⏳ تأیید انقضای فایل")
        self.exp_confirm_btn.clicked.connect(self._expire_confirm)
        self.exp_keep_btn = QPushButton("فایل را نگه دار")
        self.exp_keep_btn.clicked.connect(self._expire_keep)

        # مدیر: انتخاب بین اطلاع‌یه‌های خودش و مشاورها
        self.view_combo = None
        if api_client.role == "admin":
            self.view_combo = QComboBox()
            self.view_combo.addItem("اطلاع‌یه‌های من", None)
            try:
                for a in api_client.list_agents_for_notifications():
                    self.view_combo.addItem(f"مشاور: {a['full_name']}", a["id"])
            except ApiError:
                pass
            self.view_combo.currentIndexChanged.connect(self._reload)

        bar = QHBoxLayout()
        bar.addWidget(read_btn)
        bar.addWidget(all_btn)
        bar.addWidget(self.exp_confirm_btn)
        bar.addWidget(self.exp_keep_btn)
        bar.addStretch()
        bar.addWidget(close_btn)

        hint = QLabel("دابل‌کلیک = نمایش متن کامل و خواندن")
        lay = QVBoxLayout(self)
        if self.view_combo is not None:
            combo_row = QHBoxLayout()
            combo_row.addWidget(QLabel("نمایش:"))
            combo_row.addWidget(self.view_combo)
            combo_row.addStretch()
            lay.addLayout(combo_row)
        lay.addWidget(hint)
        lay.addWidget(self.table)
        lay.addLayout(bar)
        self._reload()

    def _selected_row(self):
        row = self.table.currentRow()
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def _update_exp_buttons(self):
        n = self._selected_row()
        is_exp = bool(n and n.get("entity_type") == "expiration")
        self.exp_confirm_btn.setEnabled(is_exp)
        self.exp_keep_btn.setEnabled(is_exp)

    def _expire_confirm(self):
        n = self._selected_row()
        if not n:
            return
        if QMessageBox.question(self, "تایید",
                "این فایل به بایگانی منتقل شود؟ (قابل بازگردانی است)") != QMessageBox.Yes:
            return
        try:
            api_client.expire_confirm(n["entity_id"])
            api_client.mark_notification_read(n["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self._reload()
        if self.on_changed:
            self.on_changed()

    def _expire_keep(self):
        n = self._selected_row()
        if not n:
            return
        try:
            api_client.expire_keep(n["entity_id"], 90)
            api_client.mark_notification_read(n["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self._reload()
        if self.on_changed:
            self.on_changed()

    def _reload(self):
        try:
            if self.view_combo is not None and self.view_combo.currentData():
                rows = api_client.list_notifications_by_user(self.view_combo.currentData())
            else:
                rows = api_client.list_notifications()
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            rows = []
        self._rows = rows
        self.table.setRowCount(len(rows))
        for r, n in enumerate(rows):
            item = QTableWidgetItem(("🔔 " if not n["is_read"] else "") + n["title"])
            item.setToolTip(n["title"] + "\n" + (n.get("body") or ""))
            if not n["is_read"]:
                item.setForeground(Qt.yellow)
            self.table.setItem(r, 0, item)
            self.table.setItem(r, 1, QTableWidgetItem((n.get("created_at") or "")[:16].replace("T", " ")))
            self.table.setItem(r, 2, QTableWidgetItem("جدید" if not n["is_read"] else "خوانده‌شده"))
        self._update_exp_buttons()

    def _mark_one(self):
        row = self.table.currentRow()
        if row < 0:
            return
        n = self._rows[row]
        QMessageBox.information(self, n["title"], (n.get("body") or "") + "\n\n" + (n.get("created_at") or "")[:16].replace("T", " "))
        if not n["is_read"]:
            try:
                api_client.mark_notification_read(n["id"])
            except ApiError as e:
                handle_api_error(self, e, "خطا")
                return
        self._reload()
        if self.on_changed:
            self.on_changed()

    def _mark_all(self):
        try:
            api_client.mark_all_notifications_read()
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self._reload()
        if self.on_changed:
            self.on_changed()


class FollowUpsTab(QWidget):
    """پیگیری روزمره — مشاور فقط کارهای خودش؛ مدیر همه را می‌بیند."""

    FILTERS = [("overdue", "⚠️ عقب‌افتاده"), ("today", "📌 امروز"),
               ("upcoming", "آینده"), ("done", "انجام‌شده"), ("all", "همه")]

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._rows = []

        self.filter_combo = QComboBox()
        for value, label in self.FILTERS:
            self.filter_combo.addItem(label, value)
        self.filter_combo.currentIndexChanged.connect(self.load_items)

        add_btn = QPushButton("پیگیری جدید")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(lambda: FollowUpDialog(on_saved=self.load_items).exec())
        edit_btn = QPushButton("ویرایش")
        edit_btn.clicked.connect(self._edit)
        done_btn = QPushButton("✔ انجام شد")
        done_btn.clicked.connect(self._done)
        open_prop_btn = QPushButton("باز کردن فایل مرتبط")
        open_prop_btn.clicked.connect(self._open_property)
        del_btn = QPushButton("حذف")
        del_btn.clicked.connect(self._delete)
        refresh_btn = QPushButton("به‌روزرسانی")
        refresh_btn.clicked.connect(self.load_items)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("نمایش:"))
        bar.addWidget(self.filter_combo)
        bar.addWidget(add_btn)
        bar.addWidget(edit_btn)
        bar.addWidget(done_btn)
        bar.addWidget(open_prop_btn)
        bar.addWidget(del_btn)
        bar.addStretch()
        bar.addWidget(refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["عنوان", "سررسید", "وضعیت", "فایل مرتبط", "توضیحات"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.doubleClicked.connect(lambda _: self._edit())

        lay = QVBoxLayout(self)
        lay.addLayout(bar)
        lay.addWidget(self.table)
        self.filter_combo.setCurrentIndex(1)
        self.load_items()

    def load_items(self):
        try:
            self._rows = api_client.list_follow_ups(when=self.filter_combo.currentData())
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.table.setRowCount(len(self._rows))
        for r, f in enumerate(self._rows):
            due = (f.get("due_date") or "—") + (f" {f['due_time']}" if f.get("due_time") else "")
            self.table.setItem(r, 0, QTableWidgetItem(f["title"]))
            self.table.setItem(r, 1, QTableWidgetItem(due))
            self.table.setItem(r, 2, QTableWidgetItem(STATUS_FA.get(f.get("status"), f.get("status", ""))))
            self.table.setItem(r, 3, QTableWidgetItem(f"#{f['property_id']}" if f.get("property_id") else "—"))
            self.table.setItem(r, 4, QTableWidgetItem(f.get("description") or ""))

    def _selected(self):
        row = self.table.currentRow()
        if 0 <= row < len(self._rows):
            return self._rows[row]
        QMessageBox.information(self, "توجه", "ابتدا یک پیگیری را انتخاب کنید.")
        return None

    def _edit(self):
        f = self._selected()
        if f:
            FollowUpDialog(data=f, on_saved=self.load_items).exec()

    def _done(self):
        f = self._selected()
        if f:
            try:
                api_client.follow_up_done(f["id"])
            except ApiError as e:
                handle_api_error(self, e, "خطا")
                return
            self.load_items()

    def _delete(self):
        f = self._selected()
        if not f:
            return
        if QMessageBox.question(self, "تایید", f"«{f['title']}» حذف شود؟") != QMessageBox.Yes:
            return
        try:
            api_client.delete_follow_up(f["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.load_items()

    def _open_property(self):
        f = self._selected()
        if not f or not f.get("property_id"):
            QMessageBox.information(self, "توجه", "این پیگیری به فایلی وصل نیست.")
            return
        try:
            prop = next((p for p in api_client.list_properties(page=1, page_size=200)["items"]
                         if p["id"] == f["property_id"]), None)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        if not prop:
            QMessageBox.information(self, "توجه", "فایل مرتبط پیدا نشد (شاید غیرفعال یا فروخته شده باشد).")
            return
        PropertyFormDialog(property_data=prop, on_saved=self.load_items).exec()