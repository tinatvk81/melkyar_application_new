from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem, QLabel,
    QLineEdit, QPushButton, QScrollArea, QFrame, QMessageBox, QDialog,
    QFormLayout, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView,
)

from api_client import api_client, ApiError
from session import handle_api_error


from settings_manager import get_theme

class Bubble(QFrame):
    def __init__(self, text, mine: bool, time_txt="", name=""):
        super().__init__()
        light = get_theme() == "light"
        # سؤال کاربر = زرد / پاسخ = آبی ملایم (روشن) یا سبز-تیرهٔ ملایم (تاریک)
        if mine:
            bg = "#f5d67a" if light else "#8a6d1f"
            txtc = "#241300" if light else "#fff3cf"
        else:
            bg = "#d6e4ff" if light else "#22304d"
            txtc = "#1c2333" if light else "#e6eeff"
        meta_c = "#6a7488" if light else "rgba(230,238,255,0.45)"
        name_c = "#b26a00" if light else "#7cc4ff"

        self.setObjectName("chatBubble")
        self.setStyleSheet(
            f"QFrame#chatBubble {{ background: {bg}; border-radius: 14px; }}"
            f"QFrame#chatBubble QLabel {{ background: transparent; color: {txtc}; border: none; }}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(3)
        if name:
            who = QLabel(name)
            who.setStyleSheet(f"color: {name_c}; font-size: 9px; font-weight: bold;")
            lay.addWidget(who)
        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.setFont(self._chat_font())
        lay.addWidget(body)
        t = QLabel(time_txt)
        t.setStyleSheet(f"color: {meta_c}; font-size: 9px;")
        t.setAlignment(Qt.AlignLeft if mine else Qt.AlignRight)
        lay.addWidget(t)

    @staticmethod
    def _chat_font():
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        f = app.font()
        f = type(f)(f)
        f.setPointSize(int(f.pointSize() + getattr(app, "chat_font_delta", 0)))
        return f

class FaqDialog(QDialog):
    """مدیریت سؤالات متداول — فقط مدیر."""
    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("سؤالات متداول چت‌بات")
        self.resize(640, 500)

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
    """گفت‌وگو: ربات پاسخ‌گو (اولین مخاطب) + چت آزاد بین همهٔ کاربران."""

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

        # --- مخاطبان (ربات = آیتم اول) ---
        left = QVBoxLayout()
        row = QHBoxLayout()
        row.addWidget(QLabel("مخاطبان"))
        row.addStretch()
        if api_client.role == "admin":
            faq_btn = QPushButton("⚙️ سؤالات ربات")
            faq_btn.setObjectName("chip")
            faq_btn.setToolTip("مدیریت سؤالات و پاسخ‌های خودکار")
            faq_btn.clicked.connect(lambda: FaqDialog().exec())
            row.addWidget(faq_btn)
        left.addLayout(row)

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

        # چیپ‌های پیشنهادی + تنظیم فونت (فقط وقتی ربات انتخاب است)
        chips_row = QHBoxLayout()
        for q in ["امکانات برنامه چیست؟", "چطور فایل ثبت کنم؟", "رمزم را فراموش کردم"]:
            b = QPushButton(q)
            b.setObjectName("chip")
            b.clicked.connect(lambda _=False, t=q: self._send_bot(t))
            chips_row.addWidget(b)
        chips_row.addWidget(QLabel("|"))
        font_dn = QPushButton("A−")
        font_dn.setObjectName("chip"); font_dn.setFixedWidth(38)
        font_up = QPushButton("A+")
        font_up.setObjectName("chip"); font_up.setFixedWidth(38)
        font_dn.clicked.connect(lambda: self._change_font(-1))
        font_up.clicked.connect(lambda: self._change_font(1))
        chips_row.addWidget(font_dn)
        chips_row.addWidget(font_up)
        chips_row.addStretch()                    # ← stretch آخر
        self.chips_widget = QWidget()
        self.chips_widget.setLayout(chips_row)
        right.addWidget(self.chips_widget)


    def _change_font(self, delta: int):
        app = QApplication.instance()
        cur = getattr(app, "chat_font_delta", 0)
        app.chat_font_delta = max(-3, min(6, cur + delta))
        # رندر مجدد حباب‌های موجود
        if self.current_peer is not None:
            self.load_conversation()
        else:
            self._load_bot_greeting()

    # ---------- ربات ----------
    def _load_bot_greeting(self):
        self._clear_bubbles()
        self._add_bubble("سلام! 👋 من چت‌بات ملک‌یارم.\n"
                         "سؤالت را بنویس یا از دکمه‌های پایین استفاده کن.\n"
                         "برای گفت‌وگو با همکارانت، از لیست مخاطبان انتخابش کن.", mine=False, name="چت‌بات")

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
        self.contacts_list.addItem(QListWidgetItem("🤖 چت‌بات (پاسخ خودکار)"))
        for c in rows:
            self.contacts_list.addItem(QListWidgetItem(f"👤 {c['full_name']}"))
        self.contacts_list.setCurrentRow(0)
        self.contacts_list.blockSignals(False)

    def _select_peer(self, row):
        if row == 0:
            self.current_peer = None
            self.peer_label.setText("🤖 چت‌بات ملک‌یار — سؤالت را بپرس")
            self.chips_widget.setVisible(True)
            self._load_bot_greeting()
            return
        idx = row - 1
        if not (0 <= idx < len(self._contacts)):
            return
        self.current_peer = self._contacts[idx]
        self.peer_label.setText(f"گفت‌وگو با: {self.current_peer['full_name']}")
        self.chips_widget.setVisible(False)
        self.load_conversation()

    def _clear_bubbles(self):
        while self.bubbles_lay.count() > 1:
            it = self.bubbles_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

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
        self._clear_bubbles()
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
        wrap = QWidget()
        w_lay = QHBoxLayout(wrap)
        w_lay.setContentsMargins(20 if mine else 0, 3, 0 if mine else 20, 3)
        b = Bubble(text, mine, time_txt, name)
        b.setMaximumWidth(620)          # حباب هرگز تمام عرض نمی‌شود
        w_lay.addWidget(b, 0 if mine else 1, Qt.AlignLeft if mine else Qt.AlignRight)
        self.bubbles_lay.insertWidget(self.bubbles_lay.count() - 1, wrap)
        sb = self.scroll.verticalScrollBar()
        QTimer.singleShot(30, lambda: sb.setValue(sb.maximum()))
    # ---------- ارسال ----------
    def _on_enter(self):
        text = self.msg_input.text().strip()
        if not text:
            return
        self.msg_input.clear()
        if self.current_peer is None:
            self._send_bot(text)
        else:
            self._send_human(text)

    def _send_bot(self, text):
        self._add_bubble(text, mine=True)
        try:
            res = api_client.bot_ask(text)
        except ApiError as e:
            handle_api_error(self, e, "خطای ربات")
            return
        self._add_bubble(res["answer"], mine=False, name="چت‌بات")

    def _send_human(self, text):
        try:
            api_client.chat_send(self.current_peer["id"], text)
        except ApiError as e:
            handle_api_error(self, e, "خطا در ارسال")
            return
        self.load_conversation()

        
# class BotPanel(QFrame):
    # """پنل شناور چت‌بات — بالای دکمهٔ ربات باز می‌شود و با هدر جابه‌جا می‌شود."""

    # def __init__(self, parent=None):
    #     super().__init__(parent)
    #     self.setObjectName("botPanel")
    #     self.setLayoutDirection(Qt.RightToLeft)
    #     self.setFixedSize(380, 520)
    #     self._drag_pos = None

    #     lay = QVBoxLayout(self)
    #     lay.setContentsMargins(0, 0, 0, 0)
    #     lay.setSpacing(0)

    #     # --- هدر (دستهٔ جابه‌جایی) ---
    #     header = QFrame()
    #     header.setObjectName("botPanelHeader")
    #     header.setCursor(Qt.SizeAllCursor)
    #     h = QHBoxLayout(header)
    #     h.setContentsMargins(14, 10, 10, 10)
    #     title = QLabel("🤖 چت‌بات ملک‌یار — پاسخگوی سوالات شماست")
    #     h.addWidget(title, 1)
    #     if api_client.role == "admin":
    #         faq_btn = QPushButton("⚙️")
    #         faq_btn.setObjectName("botClose")
    #         faq_btn.setFixedSize(28, 28)
    #         faq_btn.setToolTip("مدیریت سؤالات متداول")
    #         faq_btn.clicked.connect(lambda: FaqDialog().exec())
    #         h.addWidget(faq_btn)
    #     close_btn = QPushButton("✕")
    #     close_btn.setObjectName("botClose")
    #     close_btn.setFixedSize(28, 28)
    #     close_btn.clicked.connect(self.hide)
    #     h.addWidget(close_btn)
    #     lay.addWidget(header)

    #     # --- حباب‌ها ---
    #     self.scroll = QScrollArea()
    #     self.scroll.setWidgetResizable(True)
    #     self.scroll.setFrameShape(QFrame.NoFrame)
    #     self.holder = QWidget()
    #     self.hlay = QVBoxLayout(self.holder)
    #     self.hlay.setContentsMargins(8, 8, 8, 8)
    #     self.hlay.addStretch()
    #     self.scroll.setWidget(self.holder)
    #     lay.addWidget(self.scroll, 1)

    #     # --- چیپ‌های پیشنهادی ---
    #     chips_row = QHBoxLayout()
    #     for q in ["امکانات برنامه چیست؟", "چطور فایل ثبت کنم؟", "رمزم را فراموش کردم"]:
    #         b = QPushButton(q)
    #         b.setObjectName("chip")
    #         b.clicked.connect(lambda _=False, t=q: self._send(t))
    #         chips_row.addWidget(b)
    #     chips_row.addStretch()
    #     chips_widget = QWidget()
    #     chips_widget.setLayout(chips_row)
    #     lay.addWidget(chips_widget)

    #     # --- ورودی ---
    #     row = QHBoxLayout()
    #     row.setContentsMargins(8, 6, 8, 8)
    #     self.msg_input = QLineEdit()
    #     self.msg_input.setPlaceholderText("پیام خود را بنویسید و Enter بزنید…")
    #     self.msg_input.returnPressed.connect(lambda: self._send())
    #     send_btn = QPushButton("ارسال")
    #     send_btn.setObjectName("primary")
    #     send_btn.clicked.connect(lambda: self._send())
    #     row.addWidget(self.msg_input, 1)
    #     row.addWidget(send_btn)
    #     lay.addLayout(row)

    #     self._greet()

    # # ---------- جابه‌جایی پنل با هدر ----------
    # def _header(self):
    #     return self.findChild(QFrame, "") if False else None

    # def mousePressEvent(self, event):
    #     if event.button() == Qt.LeftButton and event.position().y() <= 46:
    #         self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
    #     else:
    #         self._drag_pos = None

    # def mouseMoveEvent(self, event):
    #     if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
    #         self.move(event.globalPosition().toPoint() - self._drag_pos)

    # def mouseReleaseEvent(self, event):
    #     self._drag_pos = None

    # # ---------- چت‌بات ----------
    # def _greet(self):
    #     self._bubble("سلام! 👋 سؤالت را دربارهٔ ملک‌یار بپرس — فایل، حسابداری، قرارداد و…", False)

    # def _bubble(self, text, mine: bool):
    #     b = Bubble(text, mine, "", "" if mine else "چت‌بات")
    #     self.hlay.insertWidget(self.hlay.count() - 1, b)
    #     sb = self.scroll.verticalScrollBar()
    #     QTimer.singleShot(30, lambda: sb.setValue(sb.maximum()))

    # def _send(self, text=None):
    #     if text is None:
    #         text = self.msg_input.text().strip()
    #     if not text:
    #         return
    #     self.msg_input.clear()
    #     self._bubble(text, True)
    #     try:
    #         res = api_client.bot_ask(text)
    #     except ApiError as e:
    #         handle_api_error(self, e, "خطای ربات")
    #         return
    #     self._bubble(res["answer"], False)