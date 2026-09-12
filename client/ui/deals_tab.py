from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QComboBox, QMessageBox, QDialog, QFormLayout, QLineEdit, QTextEdit,
    QFileDialog, QHeaderView,
)
import os
import tempfile
from api_client import api_client, ApiError
from session import handle_api_error
from ui.property_form import DEAL_TYPE_LABELS, MoneyLineEdit
from ui.jalali_date_edit import JalaliDateEdit

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
        QMessageBox.information(self, "موفق", "معامله ثبت شد.")
        self.on_saved()
        self.accept()


class PaymentDialog(QDialog):
    def __init__(self, deal_id, on_saved):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("ثبت پرداخت پورسانت")
        self.deal_id = deal_id
        self.on_saved = on_saved
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
            )
        except ApiError as e:
            handle_api_error(self, e, "خطا در ثبت پرداخت")
            return
        self.on_saved()
        self.accept()

class PaymentsDialog(QDialog):
    def __init__(self, deal, on_changed, agent_name=None):
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
            self.table.setItem(r, 2, QTableWidgetItem(p.get("paid_date") or "—"))
            self.table.setItem(r, 3, QTableWidgetItem(p.get("note") or ""))
            self.table.setItem(r, 4, QTableWidgetItem("دارد" if p.get("has_receipt") else "—"))
        self.total_label.setText(
            f"پورسانت: {_money(self.deal['commission_amount'])} — به مشاور: {_money(to_total)} — "
            f"از مشاور: {_money(from_total)} — مانده: {_money(self.deal['commission_amount'] - to_total + from_total)} تومان")

    def _add_payment(self):
        dlg = PaymentDialog(self.deal["id"], on_saved=self._reload)
        dlg.exec()
        self.on_changed()

    def _view_receipt(self):
        row = self.table.currentRow()
        if row < 0 or not self._rows[row].get("has_receipt"):
            QMessageBox.information(self, "توجه", "ابتدا پرداختی با رسید انتخاب کنید.")
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

class DealsTab(QWidget):
    """حسابداری پورسانت — فقط مدیر."""

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._deals_by_row = []
        self._agent_map = {}

        self.agent_filter = QComboBox()
        self.agent_filter.addItem("همه مشاوران", None)
        self.agent_filter.currentIndexChanged.connect(self.load_deals)

        refresh_btn = QPushButton("به‌روزرسانی")
        refresh_btn.clicked.connect(self.load_all)

        add_deal_btn = QPushButton("ثبت معامله جدید (قولنامه)")
        add_deal_btn.setObjectName("primary")
        add_deal_btn.clicked.connect(self._add_deal)

        top = QHBoxLayout()
        top.addWidget(QLabel("فیلتر مشاور:"))
        top.addWidget(self.agent_filter)
        top.addStretch()
        top.addWidget(add_deal_btn)
        top.addWidget(refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(
            ["#", "مشاور", "فایل", "مبلغ معامله", "درصد", "پورسانت", "پرداخت‌شده", "مانده", "وضعیت", "تاریخ قولنامه"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.doubleClicked.connect(lambda _: self._edit_deal())

        finalize_btn = QPushButton("قطعی‌کردن معامله")
        finalize_btn.clicked.connect(self._finalize)
        unfinalize_btn = QPushButton("↩ بازگشت به در جریان")
        unfinalize_btn.clicked.connect(self._unfinalize)
        cancel_btn = QPushButton("لغو معامله")
        cancel_btn.clicked.connect(self._cancel)
        payments_btn = QPushButton("پرداخت‌ها")
        payments_btn.clicked.connect(self._payments)
        pdf_btn = QPushButton("صورتحساب PDF")
        pdf_btn.clicked.connect(self._settlement_pdf)
        contract_btn = QPushButton("چاپ قولنامه رسمی PDF")
        contract_btn.setObjectName("primary")
        contract_btn.clicked.connect(self._contract_pdf)

        actions = QHBoxLayout()
        for b in (finalize_btn, unfinalize_btn, cancel_btn, payments_btn, pdf_btn, contract_btn):
            actions.addWidget(b)
        actions.addStretch()

        bal_title = QLabel("مانده پورسانت مشاوران")
        bal_title.setStyleSheet("font-weight: bold; color: #a5b4fc; background: transparent;")
        self.bal_table = QTableWidget()
        self.bal_table.setColumnCount(4)
        self.bal_table.setHorizontalHeaderLabels(["مشاور", "کارکرد (پورسانت قطعی)", "پرداخت‌شده", "مانده"])
        self.bal_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bal_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.bal_table.setMaximumHeight(180)
        bal_pdf_btn = QPushButton("خروجی PDF مانده‌ها")
        bal_pdf_btn.clicked.connect(self._balances_pdf)

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addLayout(actions)
        lay.addWidget(self.table)
        lay.addWidget(bal_title)
        lay.addWidget(self.bal_table)
        lay.addWidget(bal_pdf_btn)
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
        self.agent_filter.blockSignals(True)
        self.agent_filter.clear()
        self.agent_filter.addItem("همه مشاوران", None)
        for u in users:
            label = u["full_name"] + (" (مدیر)" if u.get("role") == "admin" else "")
            self.agent_filter.addItem(label, u["id"])
        self.agent_filter.blockSignals(False)
        self.load_deals()
        self.load_balances()

    def load_deals(self):
        try:
            deals = api_client.list_deals(agent_id=self.agent_filter.currentData())
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self._deals_by_row = deals
        self.table.setRowCount(len(deals))
        for r, d in enumerate(deals):
            agent = self._agent_map.get(d["agent_id"], {})
            self.table.setItem(r, 0, QTableWidgetItem(str(d["id"])))
            self.table.setItem(r, 1, QTableWidgetItem(agent.get("full_name") or ""))
            self.table.setItem(r, 2, QTableWidgetItem(f"#{d['property_id']}"))
            self.table.setItem(r, 3, QTableWidgetItem(_money(d["deal_amount"])))
            self.table.setItem(r, 4, QTableWidgetItem(f"{d['commission_percent']:g}٪"))
            self.table.setItem(r, 5, QTableWidgetItem(_money(d["commission_amount"])))
            self.table.setItem(r, 6, QTableWidgetItem(_money(d["paid_total"])))
            self.table.setItem(r, 7, QTableWidgetItem(_money(d["remaining"])))
            self.table.setItem(r, 8, QTableWidgetItem(DEAL_STATUS_LABELS.get(d["status"], d["status"])))
            self.table.setItem(r, 9, QTableWidgetItem(d.get("contract_date") or "—"))

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
                # بعد از بازگشت، فرم ویرایش را باز کن
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
        PaymentsDialog(d, agent_name=agent.get("full_name") or "", on_changed=self.load_all).exec()


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