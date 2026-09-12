from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QLabel, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QWidget,
)

from api_client import api_client, ApiError
from session import handle_api_error
from ui.property_form import DEAL_TYPE_LABELS, MoneyLineEdit, PersianDoubleSpinBox


class PresetRequestDialog(QDialog):
    def __init__(self, on_added=None):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.on_added = on_added
        self.is_admin = api_client.role == "admin"
        self.setWindowTitle("فیلترهای آماده" if self.is_admin else "فیلترهای آماده — پیشنهاد به مدیر")
        self.resize(660, 640)

        outer = QVBoxLayout(self)
        tabs = QTabWidget()

        # --- تب ۱: فیلترهای فعال ---
        active_w = QWidget()
        active_lay = QVBoxLayout(active_w)
        self.active_table = QTableWidget()
        self.active_table.setColumnCount(2)
        self.active_table.setHorizontalHeaderLabels(["نام چیپ", "فیلترها"])
        self.active_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.active_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.active_table.setSelectionBehavior(QTableWidget.SelectRows)
        if self.is_admin:
            del_btn = QPushButton("حذف فیلتر انتخاب‌شده")
            del_btn.clicked.connect(self._delete_direct)
        else:
            del_btn = QPushButton("درخواست حذف فیلتر انتخاب‌شده (برای مدیر)")
            del_btn.clicked.connect(self._request_delete)
        active_lay.addWidget(self.active_table)
        active_lay.addWidget(del_btn)
        tabs.addTab(active_w, "فیلترهای فعال")

        # --- تب ۲ (فقط مدیر): درخواست‌ها ---
        if self.is_admin:
            pend_w = QWidget()
            pend_lay = QVBoxLayout(pend_w)
            pend_lay.addWidget(QLabel("پیشنهادهای جدید (افزودن):"))
            self.add_table = QTableWidget()
            self.add_table.setColumnCount(3)
            self.add_table.setHorizontalHeaderLabels(["نام چیپ", "فیلترها", "درخواست‌دهنده"])
            self.add_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.add_table.setEditTriggers(QTableWidget.NoEditTriggers)
            pend_lay.addWidget(self.add_table)
            a_row = QHBoxLayout()
            a_ok = QPushButton("تأیید افزودن"); a_ok.setObjectName("primary")
            a_ok.clicked.connect(self._approve_add)
            a_no = QPushButton("رد/حذف"); a_no.clicked.connect(self._reject_add)
            a_row.addWidget(a_ok); a_row.addWidget(a_no); a_row.addStretch()
            pend_lay.addLayout(a_row)

            pend_lay.addWidget(QLabel("درخواست‌های حذف:"))
            self.delreq_table = QTableWidget()
            self.delreq_table.setColumnCount(3)
            self.delreq_table.setHorizontalHeaderLabels(["نام چیپ", "فیلترها", "درخواست‌دهنده"])
            self.delreq_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.delreq_table.setEditTriggers(QTableWidget.NoEditTriggers)
            pend_lay.addWidget(self.delreq_table)
            d_row = QHBoxLayout()
            d_ok = QPushButton("تأیید حذف"); d_ok.setObjectName("primary")
            d_ok.clicked.connect(self._approve_delreq)
            d_no = QPushButton("رد درخواست"); d_no.clicked.connect(self._reject_delreq)
            d_row.addWidget(d_ok); d_row.addWidget(d_no); d_row.addStretch()
            pend_lay.addLayout(d_row)
            tabs.addTab(pend_w, "درخواست‌ها (مدیر)")

        # --- تب ۳: افزودن فیلتر جدید (ترتیب درست: اول VBox، بعد فرم داخلش) ---
        new_w = QWidget()
        new_lay = QVBoxLayout(new_w)          # ← اول layout اصلی
        form = QFormLayout()                  # ← بعد فرم به‌صورت زیر-lAYOUT
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("مثلاً: آپارتمان پونک زیر ۳ میلیارد")
        self.type_combo = QComboBox()
        self.type_combo.addItem("همه", "")
        for v, l in DEAL_TYPE_LABELS.items():
            self.type_combo.addItem(l, v)
        self.city_input = QLineEdit()
        self.min_area = PersianDoubleSpinBox()
        self.max_price = MoneyLineEdit("حداکثر مبلغ (اختیاری)")
        form.addRow("نام چیپ *:", self.name_input)
        form.addRow("نوع معامله:", self.type_combo)
        form.addRow("شهر:", self.city_input)
        form.addRow("حداقل متراژ:", self.min_area)
        form.addRow("حداکثر قیمت:", self.max_price)
        new_lay.addLayout(form)

        submit_btn = QPushButton("افزودن مستقیم" if self.is_admin else "ارسال پیشنهاد به مدیر")
        submit_btn.setObjectName("primary")
        submit_btn.clicked.connect(self._submit)
        new_lay.addWidget(submit_btn)
        new_lay.addStretch()
        tabs.addTab(new_w, "افزودن فیلتر")

        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.accept)
        bottom = QHBoxLayout(); bottom.addStretch(); bottom.addWidget(close_btn)

        outer.addWidget(tabs)
        outer.addLayout(bottom)
        self._reload_all()

    def _fill(self, table, rows):
        has_req = bool(rows and rows[0].get("requester"))
        table.setColumnCount(3 if has_req else 2)
        if has_req:
            table.setHorizontalHeaderLabels(["نام چیپ", "فیلترها", "درخواست‌دهنده"])
        table.setRowCount(len(rows))
        for r, p in enumerate(rows):
            table.setItem(r, 0, QTableWidgetItem(p["name"]))
            table.setItem(r, 1, QTableWidgetItem(str(p["params"])))
            if has_req:
                table.setItem(r, 2, QTableWidgetItem(p.get("requester") or ""))

                
    def _reload_all(self):
        try:
            self._active = api_client.list_filter_presets()
            self._fill(self.active_table, self._active)
            if self.is_admin:
                self._adds = api_client.pending_filter_presets()
                self._fill(self.add_table, self._adds)
                self._delreqs = api_client.list_delete_requests()
                self._fill(self.delreq_table, self._delreqs)
        except ApiError as e:
            handle_api_error(self, e, "خطا")

    def _sel(self, table, rows):
        row = table.currentRow()
        if 0 <= row < len(rows):
            return rows[row]
        QMessageBox.information(self, "توجه", "ابتدا یک مورد را انتخاب کنید.")
        return None

    def _submit(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "خطا", "نام چیپ الزامی است.")
            return
        params = {}
        if self.type_combo.currentData():
            params["deal_type"] = self.type_combo.currentData()
        if self.city_input.text().strip():
            params["city"] = self.city_input.text().strip()
        if self.min_area.value() > 0:
            params["min_area"] = self.min_area.value()
        if self.max_price.value():
            params["max_price"] = self.max_price.value()
        if not params:
            QMessageBox.warning(self, "خطا", "حداقل یکی از فیلدها را پر کنید.")
            return
        try:
            res = api_client.create_filter_preset(name, params)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        if res.get("approved"):
            QMessageBox.information(self, "موفق", "فیلتر برای همه اضافه شد.")
            if self.on_added:
                self.on_added(name, params)
        else:
            QMessageBox.information(self, "ارسال شد", "پیشنهاد شما برای مدیر ارسال شد.")
        self._reload_all()

    def _delete_direct(self):
        p = self._sel(self.active_table, self._active)
        if not p:
            return
        if QMessageBox.question(self, "تایید", f"«{p['name']}» برای همه حذف شود؟") != QMessageBox.Yes:
            return
        try:
            api_client.delete_filter_preset(p["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self._reload_all()

    def _request_delete(self):
        p = self._sel(self.active_table, self._active)
        if not p:
            return
        try:
            api_client.request_delete_filter_preset(p["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        QMessageBox.information(self, "ارسال شد", "درخواست حذف برای مدیر ارسال شد.")

    def _approve_add(self):
        p = self._sel(self.add_table, self._adds)
        if not p:
            return
        try:
            api_client.approve_filter_preset(p["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        if self.on_added:
            self.on_added(p["name"], p["params"])
        self._reload_all()

    def _reject_add(self):
        p = self._sel(self.add_table, self._adds)
        if not p:
            return
        try:
            api_client.delete_filter_preset(p["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self._reload_all()

    def _approve_delreq(self):
        p = self._sel(self.delreq_table, self._delreqs)
        if not p:
            return
        try:
            api_client.approve_delete_filter_preset(p["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self._reload_all()

    def _reject_delreq(self):
        p = self._sel(self.delreq_table, self._delreqs)
        if not p:
            return
        try:
            api_client.reject_delete_filter_preset(p["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self._reload_all()