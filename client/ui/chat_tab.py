from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem, QLabel,
    QLineEdit, QPushButton, QScrollArea, QFrame, QMessageBox, QDialog,
    QFormLayout, QTextEdit, QTabWidget, QInputDialog,
)

from api_client import api_client, ApiError
from session import handle_api_error
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
BOT_ID = 0  # شناسهٔ فرضی ربات در لیست مخاطبان
# self.table = QTableWidget()

class Bubble(QFrame):
    def __init__(self, text, mine: bool, time_txt="", name=""):
        super().__init__()
        self.setStyleSheet(
            f"QFrame {{ background: {'rgba(245,166,35,0.22)' if mine else 'rgba(255,255,255,0.07)'};"
            f" border-radius: 12px; }}"
            "QLabel { background: transparent; }")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        if name:
            who = QLabel(name)
            who.setStyleSheet("color: #f5a623; font-size: 9px; font-weight: bold;")
            lay.addWidget(who)
        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(body)
        meta = QLabel(time_txt)
        meta.setStyleSheet("color: rgba(236,234,244,0.5); font-size: 9px;")
        meta.setAlignment(Qt.AlignLeft if mine else Qt.AlignRight)
        lay.addWidget(meta)


class FaqDialog(QDialog):
    """مدیریت سؤالات متداول — فقط مدیر."""
    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("سؤالات متداول چت‌بات")
        self.resize(640, 500)

        # self.table = QTableWidget0 = None
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["سؤال", "پاسخ خودکار"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        add_btn = QPushButton("سؤال جدید")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add)
        edit_btn = QPushButton("ویرایش")
        edit_btn.clicked.connect(self._edit)
        del_btn = QPushButton("حذف")
        del_btn.clicked.connect(self._delete)
        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.accept)

        btns = QHBoxLayout()
        for b in (add_btn, edit_btn, del_btn):
            btns.addWidget(b)
        btns.addStretch()
        btns.addWidget(close_btn)

        lay = QVBoxLayout(self)
        lay.addWidget(self.table)
        lay.addLayout(btns)
        self._reload()

    def _reload(self):
        try:
            rows = api_client.list_bot_faq()
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            rows = []
        self._rows = rows
        self.table.setRowCount(len(rows))
        for r, f in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(f["question"]))
            self.table.setItem(r, 1, QTableWidgetItem(f["answer"]))

    def _edit_dialog(self, data=None):
        dlg = QDialog(self)
        dlg.setLayoutDirection(Qt.RightToLeft)
        dlg.setWindowTitle("سؤال متداول")
        form = QFormLayout()
        q = QLineEdit(data["question"] if data else "")
        a = QTextEdit(data["answer"] if data else "")
        a.setFixedHeight(80)
        form.addRow("سؤال:", q)
        form.addRow("پاسخ:", a)
        ok = QPushButton("ذخیره"); ok.setObjectName("primary")
        ok.clicked.connect(dlg.accept)
        cancel = QPushButton("انصراف"); cancel.clicked.connect(dlg.reject)
        row = QHBoxLayout(); row.addStretch(); row.addWidget(ok); row.addWidget(cancel)
        lay = QVBoxLayout(dlg); lay.addLayout(form); lay.addLayout(row)
        if dlg.exec() != QDialog.Accepted:
            return None
        return q.text().strip(), a.toPlainText().strip()

    def _add(self):
        res = self._edit_dialog()
        if not res:
            return
        question, answer = res
        if not question or not answer:
            QMessageBox.warning(self, "خطا", "هر دو فیلد الزامی است.")
            return
        try:
            api_client.create_bot_faq(question, answer)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self._reload()

    def _edit(self):
        row = self.table.currentRow()
        if row < 0:
            return
        res = self._edit_dialog(self._rows[row])
        if not res:
            return
        question, answer = res
        try:
            api_client.update_bot_faq(self._rows[row]["id"], question, answer)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self._reload()

    def _delete(self):
        row = self.table.currentRow()
        if row < 0:
            return
        if QMessageBox.question(self, "تایید", "این سؤال حذف شود؟") != QMessageBox.Yes:
            return
        try:
            api_client.delete_bot_faq(self._rows[row]["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self._reload()


class ChatTab(QWidget):
    """گفت‌وگو: ربات پاسخ‌گو + چت آزاد بین همهٔ کاربران."""

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.current_peer = None   # None = ربات
        self._contacts = []
        self._auto_timer = QTimer(self)
        self._auto_timer.timeout.connect(self._refresh_if_open)
        self._auto_timer.start(5000)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        # --- مخاطبان ---
        left = QVBoxLayout()
        self.faq_btn = QPushButton("🤖 مدیریت سؤالات متداول")
        self.faq_btn.setVisible(api_client.role == "admin")
        self.faq_btn.clicked.connect(lambda: FaqDialog().exec())
        left.addWidget(self.faq_btn)
        left.addWidget(QLabel("مخاطبان"))
        self.contacts_list = QListWidget()
        self.contacts_list.setFixedWidth(200)
        self.contacts_list.currentRowChanged.connect(self._select_peer)
        left.addWidget(self.contacts_list, 1)
        lay.addLayout(left)

        # --- گفت‌وگو ---
        right = QVBoxLayout()
        self.peer_label = QLabel("🤖 چت‌بات ملک‌یار — سؤالت را بپرس")
        self.peer_label.setStyleSheet("font-weight: bold; color: #f5a623; background: transparent;")
        right.addWidget(self.peer_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.bubbles_holder = QWidget()
        self.bubbles_lay = QVBoxLayout(self.bubbles_holder)
        self.bubbles_lay.setContentsMargins(4, 4, 4, 4)
        self.bubbles_lay.addStretch()
        self.scroll.setWidget(self.bubbles_holder)
        right.addWidget(self.scroll, 1)

        # چیپ‌های پیشنهادی ربات
        chips_row = QHBoxLayout()
        for q in ["امکانات برنامه چیست؟", "چطور فایل جدید ثبت کنم؟", "رمزم را فراموش کردم"]:
            b = QPushButton(q)
            b.setObjectName("chip")
            b.clicked.connect(lambda _=False, t=q: self._bot_quick(t))
            chips_row.addWidget(b)
        chips_row.addStretch()
        self.chips_widget = QWidget()
        self.chips_widget.setLayout(chips_row)
        right.addWidget(self.chips_widget)

        input_row = QHBoxLayout()
        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("پیام خود را بنویسید و Enter بزنید…")
        self.msg_input.returnPressed.connect(self._send)
        send_btn = QPushButton("ارسال")
        send_btn.setObjectName("primary")
        send_btn.clicked.connect(self._send)
        input_row.addWidget(self.msg_input, 1)
        input_row.addWidget(send_btn)
        right.addLayout(input_row)

        lay.addLayout(right, 1)
        self.load_contacts()
        self._load_bot_greeting()

    # ---------- ربات ----------
    def _load_bot_greeting(self):
        self._add_bubble("سلام! 👋 من چت‌بات ملک‌یارم.\n"
                         "سؤالت را بنویس (مثلاً «چطور فایل ثبت کنم؟») یا از دکمه‌های بالا استفاده کن.\n"
                         "برای گفت‌وگو با همکاران، از لیست مخاطبان انتخابش کن.", mine=False, name="چت‌بات")

    def _bot_quick(self, text):
        self.msg_input.setText(text)
        self._send()

    # ---------- مخاطبان ----------
    def load_contacts(self):
        try:
            rows = api_client.chat_contacts()
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.contacts_list.blockSignals(True)
        self.contacts_list.clear()
        self._contacts = rows
        # آیتم اول: ربات
        bot_item = QListWidgetItem("🤖 چت‌بات (پاسخ خودکار)")
        self.contacts_list.addItem(bot_item)
        for c in rows:
            self.contacts_list.addItem(QListWidgetItem(f"👤 {c['full_name']}"))
        self.contacts_list.setCurrentRow(0)   # پیش‌فرض: ربات
        self.contacts_list.blockSignals(False)

    def _select_peer(self, row):
        if row == 0:
            self.current_peer = None   # ربات
            self.peer_label.setText("🤖 چت‌بات ملک‌یار — سؤالت را بپرس")
            self.chips_widget.setVisible(True)
            self.bubbles_lay.removeWidget  # no-op محافظ
            while self.bubbles_lay.count() > 1:
                it = self.bubbles_lay.takeAt(0)
                if it.widget():
                    it.widget().deleteLater()
            self._load_bot_greeting()
            return
        idx = row - 1
        if not (0 <= idx < len(self._contacts)):
            return
        self.current_peer = self._contacts[idx]
        self.peer_label.setText(f"گفت‌وگو با: {self.current_peer['full_name']}")
        self.chips_widget.setVisible(False)
        self.load_conversation()

    def _refresh_if_open(self):
        if self.isVisible() and self.current_peer:
            self.load_conversation()

    def load_conversation(self):
        if not self.current_peer:
            return
        try:
            rows = api_client.chat_conversation(self.current_peer["id"])
        except ApiError:
            return
        while self.bubbles_lay.count() > 1:
            it = self.bubbles_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        my_id = getattr(api_client, "user_id", None)
        names = {c["id"]: c["full_name"] for c in self._contacts}
        for m in rows:
            mine = (m["sender_id"] == my_id)
            who = "" if mine else names.get(m["sender_id"], "—")
            b = Bubble(m["body"], mine, (m.get("created_at") or "")[:16].replace("T", " "), who)
            self.bubbles_lay.insertWidget(self.bubbles_lay.count() - 1, b)
        sb = self.scroll.verticalScrollBar()
        QTimer.singleShot(50, lambda: sb.setValue(sb.maximum()))

    def _add_bubble(self, text, mine: bool, time_txt="", name=""):
        b = Bubble(text, mine, time_txt, name)
        self.bubbles_lay.insertWidget(self.bubbles_lay.count() - 1, b)
        sb = self.scroll.verticalScrollBar()
        QTimer.singleShot(30, lambda: sb.setValue(sb.maximum()))

    def _send(self):
        from PySide6.QtWidgets import QMessageBox as _QMB
        text = self.msg_input.text().strip()
        if not text:
            return
        self.msg_input.clear()

        if self.current_peer is None:
            # --- ربات ---
            self._add_bubble(text, mine=True)
            try:
                res = api_client.bot_ask(text)
            except ApiError as e:
                handle_api_error(self, e, "خطای ربات")
                return
            self._add_bubble(res["answer"], mine=False, name="چت‌بات")
            return

        # --- انسان ---
        try:
            api_client.chat_send(self.current_peer["id"], text)
        except ApiError as e:
            handle_api_error(self, e, "خطا در ارسال")
            return
        self.load_conversation()