import os
import tempfile

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView, QFileDialog,
)

from api_client import api_client, ApiError
from session import handle_api_error

STATUS_FA = {"pending": "در جریان", "finalized": "قطعی", "canceled": "لغو شده"}


def _money(v):
    return f"{int(v or 0):,}"


class MyLedgerTab(QWidget):
    """حساب من — دفتر کامل کاربر لاگین‌شده: همهٔ معامله‌های خودش (در جریان و قطعی)
    + پرداخت‌های هر معامله + مشاهده‌ی رسیدها + PDF دفتر."""

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._ledger = None

        refresh_btn = QPushButton("به‌روزرسانی")
        refresh_btn.clicked.connect(self.load)
        pdf_btn = QPushButton("PDF دفتر من")
        pdf_btn.setObjectName("primary")
        pdf_btn.clicked.connect(self._pdf)

        top = QHBoxLayout()
        top.addStretch()
        top.addWidget(pdf_btn)
        top.addWidget(refresh_btn)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-weight: bold; color: #f5a623; background: transparent;")

        lbl1 = QLabel("معامله‌های من:")
        self.deals_table = QTableWidget()
        self.deals_table.setColumnCount(9)
        self.deals_table.setHorizontalHeaderLabels(
            ["#", "فایل", "مبلغ معامله", "درصد", "پورسانت", "پرداخت‌شده", "مانده", "وضعیت", "تاریخ قولنامه"])
        self.deals_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.deals_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.deals_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.deals_table.currentCellChanged.connect(self._fill_payments)

        lbl2 = QLabel("پرداخت‌های معاملهٔ انتخاب‌شده (اگر خالی است یعنی برای این معامله پرداختی ثبت نشده):")
        self.pays_table = QTableWidget()
        self.pays_table.setColumnCount(5)
        self.pays_table.setHorizontalHeaderLabels(["مبلغ", "نوع", "تاریخ", "توضیح", "رسید"])
        self.pays_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.pays_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.pays_table.setSelectionBehavior(QAbstractItemView.SelectRows)

        receipt_btn = QPushButton("مشاهده رسید")
        receipt_btn.clicked.connect(self._view_receipt)
        pays_bar = QHBoxLayout()
        pays_bar.addWidget(receipt_btn)
        pays_bar.addStretch()

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.summary_label)
        lay.addWidget(lbl1)
        lay.addWidget(self.deals_table, 2)
        lay.addWidget(lbl2)
        lay.addWidget(self.pays_table, 1)
        lay.addLayout(pays_bar)
        self.load()

    def load(self):
        try:
            self._ledger = api_client.get_my_ledger()
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        L = self._ledger
        txt = (f"معامله: {L['deals_count']} | قطعی: {L['finalized_count']} | "
               f"کارکرد: {_money(L['earned'])} | پرداخت‌شده: {_money(L['paid_total'])} | "
               f"مانده: {_money(L['remaining'])} تومان")
        deals = L.get("deals") or []
        if not deals:
            txt += " — هنوز معامله‌ای برای شما ثبت نشده است"
        self.summary_label.setText(txt)
        self.deals_table.setRowCount(len(deals))
        for r, d in enumerate(deals):
            self.deals_table.setItem(r, 0, QTableWidgetItem(str(d["id"])))
            self.deals_table.setItem(r, 1, QTableWidgetItem(f"#{d['property_id']}"))
            self.deals_table.setItem(r, 2, QTableWidgetItem(_money(d["deal_amount"])))
            self.deals_table.setItem(r, 3, QTableWidgetItem(f"{float(d['commission_percent']):g}٪"))
            self.deals_table.setItem(r, 4, QTableWidgetItem(_money(d["commission_amount"])))
            self.deals_table.setItem(r, 5, QTableWidgetItem(_money(d["paid_total"])))
            self.deals_table.setItem(r, 6, QTableWidgetItem(_money(d["remaining"])))
            self.deals_table.setItem(r, 7, QTableWidgetItem(STATUS_FA.get(d["status"], d["status"])))
            self.deals_table.setItem(r, 8, QTableWidgetItem(d.get("contract_date") or "—"))
        # انتخاب خودکار اولین معامله → جدول پرداخت‌ها همان اول پر می‌شود (اگر پرداختی داشته باشد)
        if deals:
            self.deals_table.selectRow(0)
        else:
            self.pays_table.setRowCount(0)

    def _current_deal(self):
        row = self.deals_table.currentRow()
        if row < 0 or not self._ledger or row >= len(self._ledger.get("deals") or []):
            return None
        return self._ledger["deals"][row]

    def _fill_payments(self, *_):
        d = self._current_deal()
        pays = (d or {}).get("payments") or []
        KIND_FA = {"to_agent": "به من →", "from_agent": "از من ←"}
        self.pays_table.setRowCount(len(pays))
        for r, p in enumerate(pays):
            self.pays_table.setItem(r, 0, QTableWidgetItem(_money(p["amount"])))
            self.pays_table.setItem(r, 1, QTableWidgetItem(KIND_FA.get(p.get("kind", "to_agent"), "—")))
            self.pays_table.setItem(r, 2, QTableWidgetItem(p.get("paid_date") or "—"))
            self.pays_table.setItem(r, 3, QTableWidgetItem(p.get("note") or ""))
            self.pays_table.setItem(r, 4, QTableWidgetItem("دارد" if p.get("has_receipt") else "—"))

    def _view_receipt(self):
        prow = self.pays_table.currentRow()
        d = self._current_deal()
        if d is None or prow < 0 or prow >= len(d.get("payments") or []):
            QMessageBox.information(
                self, "توجه",
                "اول در جدول بالا یک معامله را انتخاب کن، بعد در جدول پایین یکی از پرداخت‌هایش را.\n"
                "اگر جدول پایین خالی است، یعنی برای این معامله هنوز پرداختی ثبت نشده است.")
            return
        p = d["payments"][prow]
        if not p.get("has_receipt"):
            QMessageBox.information(
                self, "توجه",
                "برای این پرداخت هنوز عکس رسیدی ثبت نشده است.\n"
                "(رسید را مدیر هنگام ثبت پرداخت، یا بعداً از پنجره‌ی «پرداخت‌ها» اضافه می‌کند.)")
            return
        path = os.path.join(tempfile.gettempdir(), f"receipt_{p['id']}.jpg")
        try:
            api_client.download_payment_receipt(p["id"], path)
            os.startfile(path)
        except ApiError as e:
            handle_api_error(self, e, "خطا در دریافت رسید")

    def _pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "ذخیره دفتر حساب", "my-ledger.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            api_client.download_my_ledger_pdf(path)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        QMessageBox.information(self, "موفق", f"ذخیره شد:\n{path}")