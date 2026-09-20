from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QComboBox, QMessageBox, QDialog, QFormLayout, QLineEdit, QTextEdit,
    QFileDialog, QHeaderView,
)
from ui.spinner import TableSpinner
from PySide6.QtWidgets import QTabWidget  
from PySide6.QtGui import QColor
import os
import tempfile
from api_client import api_client, ApiError
from session import handle_api_error
from ui.property_form import DEAL_TYPE_LABELS, MoneyLineEdit
from ui.jalali_date_edit import JalaliDateEdit
from ui.toast import Toast
from ui.jalali_util import to_jalali_str
DEAL_STATUS_LABELS = {"pending": "در جریان", "finalized": "قطعی", "canceled": "لغو شده"}


def _money(v):
    return f"{int(v or 0):,}"


class DealEditDialog(QDialog):
    def __init__(self, deal, on_saved):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.deal = deal
        self.on_saved = on_saved
        self.setWindowTitle(f"ویرایش معامله #{deal['id']}")
        form = QFormLayout()
        self.amount_input = MoneyLineEdit()
        self.amount_input.set_value(deal["deal_amount"])
        self.percent_input = QLineEdit()
        self.percent_input.setText(str(deal["commission_percent"]))
        self.date_input = JalaliDateEdit(allow_empty=True)
        if deal.get("contract_date"):
            try:
                from datetime import date as _d
                self.date_input.set_gregorian_date(_d.fromisoformat(deal["contract_date"]))
            except Exception:
                pass
        self.notes_input = QTextEdit()
        self.notes_input.setFixedHeight(60)
        self.notes_input.setPlainText(deal.get("notes") or "")
        form.addRow("مبلغ معامله:", self.amount_input)
        form.addRow("درصد پورسانت:", self.percent_input)
        form.addRow("تاریخ قولنامه:", self.date_input)
        form.addRow("توضیحات:", self.notes_input)
        save_btn = QPushButton("ذخیره"); save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("انصراف"); cancel_btn.clicked.connect(self.reject)
        row = QHBoxLayout(); row.addStretch(); row.addWidget(save_btn); row.addWidget(cancel_btn)
        lay = QVBoxLayout(self); lay.addLayout(form); lay.addLayout(row)

    def _save(self):
        payload = {"deal_amount": self.amount_input.value(),
                   "commission_percent": float(self.percent_input.text() or 0),
                   "notes": self.notes_input.toPlainText().strip() or None}
        iso = self.date_input.get_iso_string()
        if iso:
            payload["contract_date"] = iso
        try:
            api_client.update_deal(self.deal["id"], payload)
        except (ApiError, ValueError) as e:
            if isinstance(e, ValueError):
                QMessageBox.warning(self, "خطا", "درصد باید عدد باشد.")
                return
            handle_api_error(self, e, "خطا در ویرایش معامله")
            return
        self.on_saved(); self.accept()


class DealFormDialog(QDialog):
    def __init__(self, on_saved):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("ثبت معامله (قولنامه)")
        self.on_saved = on_saved
        self.resize(500, 460)

        try:
            self._agents = [u for u in api_client.list_users() if u.get("is_active")]
            self._properties = api_client.list_properties(page=1, page_size=200)["items"]
        except ApiError as e:
            handle_api_error(self, e, "خطا در دریافت داده‌ها — اتصال سرور را چک کنید")
            self._agents, self._properties = [], []

        form = QFormLayout()
        self.prop_combo = QComboBox()
        for p in self._properties:
            t = DEAL_TYPE_LABELS.get(p.get("deal_type"), "")
            self.prop_combo.addItem(f"#{p['id']} — {t} — {p.get('city','')} — {p.get('address') or ''}", p["id"])
        self.agent_combo = QComboBox()
        self.agent2_combo = QComboBox()
        self.agent2_combo.addItem("— بدون مشارکت —", None)
        for a in self._agents:
            label = a["full_name"] + (" (مدیر)" if a.get("role") == "admin" else "")
            self.agent2_combo.addItem(label, a["id"])
        self.share2_input = QLineEdit()
        self.share2_input.setPlaceholderText("درصد سهم مشاور دوم (مثلاً 15)")
        form.addRow("مشاور دوم (اختیاری):", self.agent2_combo)
        form.addRow("سهم مشاور دوم (%):", self.share2_input)
        for a in self._agents:
            label = a["full_name"] + (" (مدیر)" if a.get("role") == "admin" else "")
            self.agent_combo.addItem(label, a["id"])
        self.amount_input = MoneyLineEdit("مبلغ کل معامله (تومان)")
        self.percent_input = QLineEdit()
        self.percent_input.setPlaceholderText("خالی = درصد پیش‌فرض مشاور")
        self.date_input = JalaliDateEdit(allow_empty=True)
        self.notes_input = QTextEdit()
        self.notes_input.setFixedHeight(60)

        if not self._agents:
            QMessageBox.warning(self, "توجه",
                "هیچ مشاور فعالی یافت نشد. ابتدا در «مشاوران و مدیریت» یک حساب با نقش «مشاور» بسازید.")

        form.addRow("فایل ملکی:", self.prop_combo)
        form.addRow("مشاور:", self.agent_combo)
        form.addRow("مبلغ معامله:", self.amount_input)
        form.addRow("درصد پورسانت:", self.percent_input)
        form.addRow("تاریخ قولنامه:", self.date_input)
        form.addRow("توضیحات:", self.notes_input)

        save_btn = QPushButton("ثبت معامله")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self.handle_save)
        cancel_btn = QPushButton("انصراف")
        cancel_btn.clicked.connect(self.reject)
        btns = QHBoxLayout()
        btns.addStretch()
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addLayout(btns)

    def handle_save(self):
        if self.prop_combo.currentIndex() < 0 or self.agent_combo.currentIndex() < 0:
            QMessageBox.warning(self, "خطا", "فایل و مشاور را انتخاب کنید.")
            return
        amount = self.amount_input.value()
        if not amount:
            QMessageBox.warning(self, "خطا", "مبلغ معامله الزامی است.")
            return
        payload = {
            "property_id": self.prop_combo.currentData(),
            "agent_id": self.agent_combo.currentData(),
            "deal_amount": amount,
        }
        try:
            pct = self.percent_input.text().replace("٪", "").strip()
            if pct:
                payload["commission_percent"] = float(pct)
        except ValueError:
            QMessageBox.warning(self, "خطا", "درصد پورسانت باید عدد باشد.")
            return
        if self.agent2_combo.currentData():
            payload["agent2_id"] = self.agent2_combo.currentData()
            try:
                s2 = float(self.share2_input.text().replace("٪", "").strip())
            except ValueError:
                QMessageBox.warning(self, "خطا", "سهم مشاور دوم باید عدد باشد.")
                return
            if not (0 < s2 < (payload.get("commission_percent") or 100)):
                QMessageBox.warning(self, "خطا", "سهم دوم باید بین صفر و درصد کل باشد.")
                return
            payload["commission_percent_agent2"] = s2


        iso = self.date_input.get_iso_string()
        if iso:
            payload["contract_date"] = iso
        if self.notes_input.toPlainText().strip():
            payload["notes"] = self.notes_input.toPlainText().strip()

        try:
            api_client.create_deal(payload)
        except ApiError as e:
            handle_api_error(self, e, "خطا در ثبت معامله")
            return
        Toast.show("✅ معامله ثبت شد")
        self.on_saved()
        self.accept()

class PaymentDialog(QDialog):
    def __init__(self, deal_id, on_saved, to_user=None):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.deal_id = deal_id
        self.on_saved = on_saved
        self._to_user = to_user
        self.setWindowTitle("ثبت پرداخت پورسانت")
        self.resize(430, 330)

        form = QFormLayout()
        self.kind_combo = QComboBox()
        self.kind_combo.addItem("پرداخت به مشاور", "to_agent")
        self.kind_combo.addItem("دریافت از مشاور (جبران بدهی)", "from_agent")
        self.amount_input = MoneyLineEdit("مبلغ پرداخت (تومان)")
        self.date_input = JalaliDateEdit(allow_empty=True)
        self.note_input = QLineEdit()
        self.receipt_input = QLineEdit()

        browse = QPushButton("…")
        browse.setFixedWidth(36)
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.receipt_input, 1)
        row.addWidget(browse)
        wrap = QWidget(); wrap.setLayout(row)
        form.addRow("نوع:", self.kind_combo)
        form.addRow("مبلغ:", self.amount_input)
        form.addRow("تاریخ پرداخت:", self.date_input)
        form.addRow("توضیح:", self.note_input)
        form.addRow("عکس رسید:", wrap)

        save_btn = QPushButton("ثبت پرداخت")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self.handle_save)
        cancel_btn = QPushButton("انصراف")
        cancel_btn.clicked.connect(self.reject)
        btns = QHBoxLayout(); btns.addStretch(); btns.addWidget(save_btn); btns.addWidget(cancel_btn)

        lay = QVBoxLayout(self); lay.addLayout(form); lay.addLayout(btns)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "انتخاب عکس رسید", "", "Images (*.jpg *.jpeg *.png *.webp)")
        if path:
            self.receipt_input.setText(path)

    def handle_save(self):
        amount = self.amount_input.value()
        if not amount:
            QMessageBox.warning(self, "خطا", "مبلغ الزامی است.")
            return
        try:
            api_client.add_deal_payment(
                self.deal_id, amount,
                paid_date=self.date_input.get_iso_string(),
                note=self.note_input.text().strip() or None,
                receipt_path=self.receipt_input.text().strip() or None,
                kind=self.kind_combo.currentData(),
                to_user=self._to_user,
            )
        except ApiError as e:
            handle_api_error(self, e, "خطا در ثبت پرداخت")
            return
        self.on_saved()
        self.accept()

class PaymentsDialog(QDialog):
    def __init__(self, deal, on_changed, agent_name=None, agent2_name=None):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.deal = deal
        self.on_changed = on_changed
        self.setWindowTitle(f"پرداخت‌های معامله #{deal['id']}")
        self.resize(640, 450)

        head = QLabel(f"مشاور: {agent_name or '—'} — معامله #{deal['id']} — فایل #{deal['property_id']}")
        head.setStyleSheet("font-weight: bold; color: #a5b4fc; background: transparent;")

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["مبلغ", "نوع", "تاریخ", "توضیح", "رسید"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.total_label = QLabel("")
        add_btn = QPushButton("افزودن پرداخت")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add_payment)
        view_btn = QPushButton("مشاهده رسید")
        view_btn.clicked.connect(self._view_receipt)
        attach_btn = QPushButton("افزودن/تعویض رسید")
        attach_btn.clicked.connect(self._attach_receipt)
        del_btn = QPushButton("حذف پرداخت انتخاب‌شده")
        del_btn.clicked.connect(self._delete_payment)
        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.accept)


            
        btns = QHBoxLayout()
        btns.addWidget(add_btn)
        btns.addWidget(view_btn)
        btns.addWidget(attach_btn)
        btns.addWidget(del_btn)
        btns.addStretch()
        btns.addWidget(close_btn)

        lay = QVBoxLayout(self)
        lay.addWidget(head)
        self.to_user_combo = None
        if deal.get("agent2_id"):
            self.to_user_combo = QComboBox()
            self.to_user_combo.addItem(f"سهم مشاور: {agent_name or '—'}", deal["agent_id"])
            a2 = agent2_name or f"#{deal['agent2_id']}"
            self.to_user_combo.addItem(f"سهم مشاور: {a2}", deal["agent2_id"])
            lay.addWidget(QLabel("پرداخت جدید به سهمِ:"))
            lay.addWidget(self.to_user_combo)
        lay.addWidget(self.total_label)
        lay.addWidget(self.table)
        lay.addLayout(btns)
        self._reload()

    def _reload(self):
        try:
            rows = api_client.list_deal_payments(self.deal["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self._rows = rows
        KIND_FA = {"to_agent": "به مشاور →", "from_agent": "از مشاور ←"}
        to_total = sum(p["amount"] for p in rows if p.get("kind", "to_agent") == "to_agent")
        from_total = sum(p["amount"] for p in rows if p.get("kind") == "from_agent")
        self.table.setRowCount(len(rows))
        for r, p in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(_money(p["amount"])))
            self.table.setItem(r, 1, QTableWidgetItem(KIND_FA.get(p.get("kind", "to_agent"), "—")))
            self.table.setItem(r, 2, QTableWidgetItem(to_jalali_str(p.get("paid_date"))))
            self.table.setItem(r, 3, QTableWidgetItem(p.get("note") or ""))
            self.table.setItem(r, 4, QTableWidgetItem("دارد" if p.get("has_receipt") else "—"))

        self.total_label.setText(
            f"پورسانت: {_money(self.deal['commission_amount'])} — به مشاور: {_money(to_total)} — "
            f"از مشاور: {_money(from_total)} — مانده: {_money(self.deal['commission_amount'] - to_total + from_total)} تومان")

    def _add_payment(self):
        to_user = self.to_user_combo.currentData() if self.to_user_combo else None
        dlg = PaymentDialog(self.deal["id"], on_saved=self._reload, to_user=to_user)
        dlg.exec()
        self.on_changed()

    def _view_receipt(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "توجه", "ابتدا یک پرداخت را انتخاب کنید.")
            return
        if not self._rows[row].get("has_receipt"):
            QMessageBox.information(
                self, "توجه",
                "برای این پرداخت هنوز رسیدی ثبت نشده است.\n"
                "با دکمه‌ی «افزودن/تعویض رسید» می‌توانی عکس رسید را به همین پرداخت اضافه کنی.")
            return
        path = os.path.join(tempfile.gettempdir(), f"receipt_{self._rows[row]['id']}.jpg")
        try:
            api_client.download_payment_receipt(self._rows[row]["id"], path)
            os.startfile(path)
        except ApiError as e:
            handle_api_error(self, e, "خطا در دریافت رسید")


    def _attach_receipt(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "توجه", "ابتدا یک پرداخت را انتخاب کنید.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "انتخاب عکس رسید", "", "Images (*.jpg *.jpeg *.png *.webp)")
        if not path:
            return
        try:
            api_client.upload_payment_receipt(self._rows[row]["id"], path)
        except ApiError as e:
            handle_api_error(self, e, "خطا در ثبت رسید")
            return
        self._reload()

    def _delete_payment(self):
        row = self.table.currentRow()
        if row < 0:
            return
        if QMessageBox.question(self, "تایید", "این پرداخت حذف شود؟") != QMessageBox.Yes:
            return
        try:
            api_client.delete_deal_payment(self._rows[row]["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self._reload()
        self.on_changed()

class BackupDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("بکاپ دیتابیس")
        self.resize(560, 400)
        self._rows = []

        run_btn = QPushButton("💾 ساخت بکاپ الان")
        run_btn.setObjectName("primary")
        run_btn.clicked.connect(self._run)
        dl_btn = QPushButton("دانلود انتخاب‌شده")
        dl_btn.clicked.connect(self._download)
        refresh_btn = QPushButton("به‌روزرسانی")
        refresh_btn.clicked.connect(self._reload)
        close_btn = QPushButton("بستن"); close_btn.clicked.connect(self.accept)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["فایل بکاپ", "حجم (بایت)"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        bar = QHBoxLayout(); bar.addWidget(run_btn); bar.addWidget(dl_btn)
        bar.addWidget(refresh_btn); bar.addStretch(); bar.addWidget(close_btn)
        hint = QLabel("هر شب ۰۲:۳۰ خودکار ساخته می‌شود — ۱۴ نسخهٔ آخر نگه‌داری می‌شود.")
        lay = QVBoxLayout(self); lay.addWidget(hint); lay.addWidget(self.table); lay.addLayout(bar)
        self._reload()

    def _reload(self):
        try:
            self._rows = api_client.list_backups()
        except ApiError as e:
            handle_api_error(self, e, "خطا"); self._rows = []
        self.table.setRowCount(len(self._rows))
        for r, b in enumerate(self._rows):
            self.table.setItem(r, 0, QTableWidgetItem(b["filename"]))
            self.table.setItem(r, 1, QTableWidgetItem(f"{b['size']:,}"))

    def _run(self):
        try:
            res = api_client.run_backup()
        except ApiError as e:
            handle_api_error(self, e, "خطا در بکاپ"); return
        Toast.show(f"✅ بکاپ ساخته شد: {res['filename']}")
        self._reload()

    def _download(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "توجه", "ابتدا یک بکاپ انتخاب کنید."); return
        path, _ = QFileDialog.getSaveFileName(self, "ذخیره بکاپ", self._rows[row]["filename"], "Backup (*.json.gz)")
        if not path: return
        try:
            api_client.download_backup(self._rows[row]["filename"], path)
        except ApiError as e:
            handle_api_error(self, e, "خطا"); return
        QMessageBox.information(self, "موفق", f"ذخیره شد:\n{path}")


class DealsTab(QWidget):
    """حسابداری پورسانت — فقط مدیر. سه تب: معامله‌ها / مانده‌ها / دفتر فردی."""

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._deals_by_row = []
        self._agent_map = {}
        self._ind_ledger = None

        self.agent_filter = QComboBox()
        self.agent_filter.addItem("همه مشاوران", None)
        self.agent_filter.currentIndexChanged.connect(self.load_deals)

        self.status_filter = QComboBox()
        self.status_filter.addItem("همه وضعیت‌ها", None)
        for v, l in DEAL_STATUS_LABELS.items():
            self.status_filter.addItem(l, v)
        self.status_filter.currentIndexChanged.connect(self.load_deals)

        self.period_combo = QComboBox()
        self.period_combo.addItem("همهٔ زمان‌ها", None)
        self.period_combo.addItem("۳۰ روز اخیر", 30)
        self.period_combo.addItem("۹۰ روز اخیر", 90)
        self.period_combo.addItem("۱ سال اخیر", 365)
        self.period_combo.currentIndexChanged.connect(self.load_deals)

        refresh_btn = QPushButton("به‌روزرسانی")
        refresh_btn.clicked.connect(self.load_all)
        add_deal_btn = QPushButton("ثبت معامله جدید (قولنامه)")
        add_deal_btn.setObjectName("primary")
        add_deal_btn.clicked.connect(self._add_deal)

        top = QHBoxLayout()
        top.addWidget(QLabel("مشاور:")); top.addWidget(self.agent_filter)
        top.addWidget(QLabel("وضعیت:")); top.addWidget(self.status_filter)
        top.addWidget(QLabel("بازه:")); top.addWidget(self.period_combo)

        top.addStretch()
        top.addWidget(add_deal_btn); top.addWidget(refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(
            ["#", "مشاور", "فایل", "مبلغ معامله", "درصد", "پورسانت", "پرداخت‌شده", "مانده", "وضعیت", "تاریخ قولنامه"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.doubleClicked.connect(lambda _: self._edit_deal())
        self.count_label = QLabel("")
        finalize_btn = QPushButton("قطعی‌کردن"); finalize_btn.clicked.connect(self._finalize)
        unfinalize_btn = QPushButton("↩ بازگشت به در جریان"); unfinalize_btn.clicked.connect(self._unfinalize)
        cancel_btn = QPushButton("لغو معامله"); cancel_btn.clicked.connect(self._cancel)
        payments_btn = QPushButton("پرداخت‌ها"); payments_btn.clicked.connect(self._payments)
        pdf_btn = QPushButton("صورتحساب PDF"); pdf_btn.clicked.connect(self._settlement_pdf)
        contract_btn = QPushButton("چاپ قولنامه رسمی PDF"); contract_btn.setObjectName("primary")
        contract_btn.clicked.connect(self._contract_pdf)
        actions = QHBoxLayout()

        excel_btn = QPushButton("خروجی اکسل"); excel_btn.clicked.connect(self._deals_excel)

        for b in (finalize_btn, unfinalize_btn, cancel_btn, payments_btn, pdf_btn, contract_btn, excel_btn):
            actions.addWidget(b)
        actions.addStretch()
        actions.addWidget(self.count_label)
        deals_w = QWidget(); deals_lay = QVBoxLayout(deals_w)
        deals_lay.addLayout(actions)
        deals_lay.addWidget(self.table)



        self.bal_table = QTableWidget()
        self.bal_table.setColumnCount(4)
        self.bal_table.setHorizontalHeaderLabels(["مشاور", "کارکرد (پورسانت قطعی)", "پرداخت‌شده", "مانده"])
        self.bal_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bal_table.setEditTriggers(QTableWidget.NoEditTriggers)
        bal_pdf_btn = QPushButton("خروجی PDF مانده‌ها")
        bal_pdf_btn.clicked.connect(self._balances_pdf)
        bal_w = QWidget(); bal_lay = QVBoxLayout(bal_w)
        bal_lay.addWidget(self.bal_table); bal_lay.addWidget(bal_pdf_btn)
        backup_btn = QPushButton("💾 بکاپ"); backup_btn.clicked.connect(lambda: BackupDialog().exec())
        actions.addWidget(backup_btn)
        ind_w = QWidget(); ind_lay = QVBoxLayout(ind_w)
        a_row = QHBoxLayout()
        a_row.addWidget(QLabel("مشاور:"))
        self.individual_combo = QComboBox()
        self.individual_combo.setMinimumWidth(220)
        self.individual_combo.currentIndexChanged.connect(self._load_individual)
        a_row.addWidget(self.individual_combo); a_row.addStretch()
        ind_pdf_btn = QPushButton("PDF دفتر این مشاور")
        ind_pdf_btn.clicked.connect(self._ind_ledger_pdf)
        a_row.addWidget(ind_pdf_btn)
        all_pdf_btn = QPushButton("PDF دفتر همه (یک فایل)")
        all_pdf_btn.setObjectName("primary")
        all_pdf_btn.clicked.connect(self._all_ledgers_pdf)
        a_row.addWidget(all_pdf_btn)
        self.individual_label = QLabel("")
        self.individual_label.setStyleSheet("font-weight: bold; color: #f5a623; background: transparent;")
        a_row.addWidget(self.individual_label)
        ind_lay.addLayout(a_row)

        self.ind_table = QTableWidget()
        self.ind_table.setColumnCount(9)
        self.ind_table.setHorizontalHeaderLabels(
            ["#", "فایل", "مبلغ معامله", "درصد", "پورسانت", "پرداخت‌شده", "مانده", "وضعیت", "تاریخ"])
        self.ind_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.ind_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.ind_table.setSelectionBehavior(QTableWidget.SelectRows)
        ind_lay.addWidget(self.ind_table)

      


        tabs = QTabWidget()
        tabs.addTab(deals_w, "معامله‌ها")
        tabs.addTab(bal_w, "مانده‌ها")
        tabs.addTab(ind_w, "دفتر حساب فردی")

        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addWidget(tabs)
        self.load_all()

    def _contract_pdf(self):
        d = self._selected_deal()
        if not d:
            return
        path, _ = QFileDialog.getSaveFileName(self, "ذخیره قولنامه", f"contract-{d['id']}.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            api_client.download_contract_pdf(d["id"], path)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        QMessageBox.information(self, "موفق", f"ذخیره شد:\n{path}")

    def _unfinalize(self):
        d = self._selected_deal()
        if not d:
            return
        if d["status"] != "finalized":
            QMessageBox.information(self, "توجه", "فقط معامله‌ی قطعی‌شده قابل بازگشت است.")
            return
        if QMessageBox.question(
            self, "تایید",
            f"معامله #{d['id']} از حالت قطعی خارج شود؟\n"
            "فایل ملکی دوباره فعال می‌شود و می‌توانی مبلغ/درصد را اصلاح کنی."
        ) != QMessageBox.Yes:
            return
        try:
            api_client.unfinalize_deal(d["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.load_all()

    def load_all(self):
        try:
            users = api_client.list_users()
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self._agent_map = {u["id"]: u for u in users}

        def user_label(u):
            label = u["full_name"] + (" (مدیر)" if u.get("role") == "admin" else "")
            if not u.get("is_active"):
                label += " — غیرفعال"
            return label

        self.agent_filter.blockSignals(True)
        self.agent_filter.clear()
        self.agent_filter.addItem("همه مشاوران", None)
        for u in users:
            self.agent_filter.addItem(user_label(u), u["id"])
        self.agent_filter.blockSignals(False)

        self.individual_combo.blockSignals(True)
        self.individual_combo.clear()
        self.individual_combo.addItem("— انتخاب مشاور —", None)
        for u in users:
            self.individual_combo.addItem(user_label(u), u["id"])
        self.individual_combo.blockSignals(False)

        self.load_deals()
        self.load_balances()

    def _load_individual(self):
        uid = self.individual_combo.currentData()
        self.ind_table.setRowCount(0)
        self.individual_label.setText("")
        self._ind_ledger = None
        if uid is None:
            return
        try:
            self._ind_ledger = api_client.get_user_ledger(uid)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        L = self._ind_ledger
        deals = L.get("deals") or []
        self.ind_table.setRowCount(len(deals))
        for r, d in enumerate(deals):
            self.ind_table.setItem(r, 0, QTableWidgetItem(str(d["id"])))
            self.ind_table.setItem(r, 1, QTableWidgetItem(f"#{d['property_id']}"))
            self.ind_table.setItem(r, 2, QTableWidgetItem(_money(d["deal_amount"])))
            self.ind_table.setItem(r, 3, QTableWidgetItem(f"{float(d['commission_percent']):g}٪"))
            self.ind_table.setItem(r, 4, QTableWidgetItem(_money(d["commission_amount"])))
            self.ind_table.setItem(r, 5, QTableWidgetItem(_money(d["paid_total"])))
            self.ind_table.setItem(r, 6, QTableWidgetItem(_money(d["remaining"])))
            st_item = QTableWidgetItem(DEAL_STATUS_LABELS.get(d["status"], d["status"]))
            st_item.setForeground(QColor({"finalized": "#22c55e", "pending": "#f5a623", "canceled": "#ef4444"}.get(d["status"], "#eceaf4")))
            _f2 = st_item.font(); _f2.setBold(True); st_item.setFont(_f2)
            self.ind_table.setItem(r, 7, st_item)
            self.ind_table.setItem(r, 8, QTableWidgetItem(d.get("contract_date") or "—"))
        self.individual_label.setText(
            f"معامله: {L['deals_count']} | قطعی: {L['finalized_count']} | کارکرد: {_money(L['earned'])} | "
            f"پرداخت‌شده: {_money(L['paid_total'])} | مانده: {_money(L['remaining'])} تومان")


    def _ind_ledger_pdf(self):
        uid = self.individual_combo.currentData()
        if uid is None:
            QMessageBox.information(self, "توجه", "ابتدا مشاور را انتخاب کنید.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "ذخیره دفتر حساب", f"ledger-{uid}.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            api_client.download_user_ledger_pdf(uid, path)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        QMessageBox.information(self, "موفق", f"ذخیره شد:\n{path}")

    def _all_ledgers_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "ذخیره دفتر همه", "all-ledgers.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            api_client.download_all_ledgers_pdf(path)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        QMessageBox.information(self, "موفق", f"ذخیره شد:\n{path}")

    def load_deals(self):
        TableSpinner.show(self.table)
        try:
            deals = api_client.list_deals(agent_id=self.agent_filter.currentData())
        except ApiError as e:
            TableSpinner.hide(self.table)
            handle_api_error(self, e, "خطا")
            return
        TableSpinner.hide(self.table)

        # فیلتر وضعیت — قبلاً هیچ‌جا اعمال نمی‌شد و برای همین تغییرش اثری نداشت
        st = self.status_filter.currentData()
        if st:
            deals = [d for d in deals if d.get("status") == st]

        # فیلتر بازه‌ی زمانی (قبل از رندر)
        days = self.period_combo.currentData()
        if days:
            from datetime import date, timedelta
            cutoff = date.today() - timedelta(days=days)
            def _in_range(d):
                cd = d.get("contract_date") or (d.get("created_at") or "")[:10]
                return bool(cd) and cd >= cutoff.isoformat()
            deals = [d for d in deals if _in_range(d)]

        self._deals_by_row = deals
        self.table.setRowCount(len(deals))
        for r, d in enumerate(deals):
            agent = self._agent_map.get(d["agent_id"], {})
            self.table.setItem(r, 0, QTableWidgetItem(str(d["id"])))
            name = agent.get("full_name") or ""
            if d.get("agent2_id"):
                a2 = self._agent_map.get(d["agent2_id"], {})
                name += f" 🤝 {a2.get('full_name') or '#'+str(d['agent2_id'])}"
            self.table.setItem(r, 1, QTableWidgetItem(name))
            self.table.setItem(r, 2, QTableWidgetItem(f"#{d['property_id']}"))
            self.table.setItem(r, 3, QTableWidgetItem(_money(d["deal_amount"])))
            self.table.setItem(r, 4, QTableWidgetItem(f"{d['commission_percent']:g}٪"))
            self.table.setItem(r, 5, QTableWidgetItem(_money(d["commission_amount"])))
            self.table.setItem(r, 6, QTableWidgetItem(_money(d["paid_total"])))
            self.table.setItem(r, 7, QTableWidgetItem(_money(d["remaining"])))

            st_item = QTableWidgetItem(DEAL_STATUS_LABELS.get(d["status"], d["status"]))
            _st_colors = {"finalized": "#22c55e", "pending": "#f5a623", "canceled": "#ef4444"}
            st_item.setForeground(QColor(_st_colors.get(d["status"], "#eceaf4")))
            _f = st_item.font(); _f.setBold(True); st_item.setFont(_f)
            
            self.table.setItem(r, 8, st_item)
            self.table.setItem(r, 9, QTableWidgetItem(to_jalali_str(d.get("contract_date"))))


        if not deals:
            self.count_label.setText("هیچ معامله‌ای با این فیلترها پیدا نشد — «بازه» را روی «همهٔ زمان‌ها» هم تست کن.")
        else:
            self.count_label.setText(f"تعداد: {len(deals)} معامله")



    def load_balances(self):
        try:
            rows = api_client.get_balances()
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.bal_table.setRowCount(len(rows))
        for r, b in enumerate(rows):
            self.bal_table.setItem(r, 0, QTableWidgetItem(b["full_name"]))
            self.bal_table.setItem(r, 1, QTableWidgetItem(_money(b["earned"])))
            self.bal_table.setItem(r, 2, QTableWidgetItem(_money(b["paid"])))
            self.bal_table.setItem(r, 3, QTableWidgetItem(_money(b["remaining"])))

    def _selected_deal(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._deals_by_row):
            QMessageBox.information(self, "توجه", "ابتدا یک معامله را انتخاب کنید.")
            return None
        return self._deals_by_row[row]

    def _add_deal(self):
        DealFormDialog(on_saved=self.load_all).exec()

    def _finalize(self):
        d = self._selected_deal()
        if not d:
            return
        if d["status"] == "finalized":
            QMessageBox.information(self, "توجه", "این معامله قبلاً قطعی شده است — نیازی به تکرار نیست.")
            return
        if QMessageBox.question(
            self, "تایید",
            f"معامله #{d['id']} قطعی شود؟\n(پورسانت {_money(d['commission_amount'])} تومان رسمی می‌شود و فایل به بایگانی می‌رود)"
        ) != QMessageBox.Yes:
            return
        try:
            api_client.finalize_deal(d["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.load_all()

    def _cancel(self):
        d = self._selected_deal()
        if not d:
            return
        if d["status"] == "finalized":
            QMessageBox.information(self, "توجه", "معامله‌ی قطعی‌شده قابل لغو نیست. برای جبران، «دریافت از مشاور» ثبت کنید.")
            return
        if QMessageBox.question(self, "تایید", f"معامله #{d['id']} لغو شود؟") != QMessageBox.Yes:
            return
        try:
            api_client.cancel_deal(d["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.load_all()

    def _edit_deal(self):
        d = self._selected_deal()
        if not d:
            return
        if d["status"] == "canceled":
            QMessageBox.information(self, "توجه", "معامله‌ی لغوشده قابل ویرایش نیست.")
            return
        if d["status"] == "finalized":
            ans = QMessageBox.question(
                self, "معامله قطعی است",
                "ویرایش مبلغ/درصد معامله‌ی قطعی‌شده مجاز نیست.\n"
                "«بازگشت به در جریان» بزنم تا ویرایش کنی؟ (فایل ملکی دوباره فعال می‌شود)",
            )
            if ans == QMessageBox.Yes:
                try:
                    api_client.unfinalize_deal(d["id"])
                except ApiError as e:
                    handle_api_error(self, e, "خطا")
                    return
                self.load_all()
                fresh = next((x for x in self._deals_by_row if x["id"] == d["id"]), None)
                if fresh:
                    DealEditDialog(fresh, on_saved=self.load_all).exec()
            return
        DealEditDialog(d, on_saved=self.load_all).exec()

    def _payments(self):
        d = self._selected_deal()
        if not d:
            return
        if d["status"] == "canceled":
            QMessageBox.information(self, "توجه", "برای معامله‌ی لغوشده پرداخت ثبت نمی‌شود.")
            return
        agent = self._agent_map.get(d["agent_id"], {})
        d2 = self._agent_map.get(d.get("agent2_id"), {})
        PaymentsDialog(d, agent_name=agent.get("full_name") or "",
                       agent2_name=(d2.get("full_name") or f"#{d.get('agent2_id')}") if d.get("agent2_id") else None,
                       on_changed=self.load_all).exec()


    def _settlement_pdf(self):
        d = self._selected_deal()
        if not d:
            return
        path, _ = QFileDialog.getSaveFileName(self, "ذخیره صورتحساب", f"settlement-{d['id']}.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            api_client.download_settlement_pdf(d["id"], path)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        QMessageBox.information(self, "موفق", f"ذخیره شد:\n{path}")

    def _balances_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "ذخیره مانده‌ها", "agent-balances.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            api_client.download_balances_pdf(path)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        QMessageBox.information(self, "موفق", f"ذخیره شد:\n{path}")

    def _deals_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "ذخیره اکسل معامله‌ها", "deals.xlsx", "Excel Files (*.xlsx)")
        if not path:
            return
        try:
            api_client.export_deals_excel(path)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        QMessageBox.information(self, "موفق", f"فایل اکسل ذخیره شد:\n{path}")
