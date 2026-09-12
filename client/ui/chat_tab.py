from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem, QLabel,
    QLineEdit, QPushButton, QScrollArea, QFrame, QAbstractItemView, QMessageBox,
)

from api_client import api_client, ApiError
from session import handle_api_error


class Bubble(QFrame):
    def __init__(self, text, mine: bool, time_txt=""):
        super().__init__()
        self.setStyleSheet(
            f"QFrame {{ background: {'rgba(245,166,35,0.22)' if mine else 'rgba(255,255,255,0.07)'};"
            f" border-radius: 12px; padding: 4px; }}"
            "QLabel { background: transparent; }")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(body)
        meta = QLabel(time_txt)
        meta.setStyleSheet("color: rgba(236,234,244,0.5); font-size: 9px;")
        meta.setAlignment(Qt.AlignLeft if mine else Qt.AlignRight)
        lay.addWidget(meta)


class ChatTab(QWidget):
    """گفت‌وگوی داخلی — مشاور فقط با مدیر؛ مدیر با همه."""

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.current_peer = None
        self._auto_timer = QTimer(self)
        self._auto_timer.timeout.connect(self._refresh_if_open)
        self._auto_timer.start(5000)  # هر ۵ ثانیه پیام‌های جدید

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        # --- ستون مخاطبان ---
        left = QVBoxLayout()
        left.addWidget(QLabel("مخاطبان"))
        self.contacts_list = QListWidget()
        self.contacts_list.setFixedWidth(200)
        self.contacts_list.currentRowChanged.connect(self._select_peer)
        left.addWidget(self.contacts_list, 1)
        lay.addLayout(left)

        # --- ستون گفت‌وگو ---
        right = QVBoxLayout()

        self.peer_label = QLabel("— برای شروع، یک مخاطب انتخاب کنید —")
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

    def load_contacts(self):
        try:
            rows = api_client.chat_contacts()
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.contacts_list.blockSignals(True)
        self.contacts_list.clear()
        self._contacts = rows
        for c in rows:
            it = QListWidgetItem(f"👤 {c['full_name']}")
            self.contacts_list.addItem(it)
        self.contacts_list.blockSignals(False)

    def _select_peer(self, row):
        if not (0 <= row < len(self._contacts)):
            return
        self.current_peer = self._contacts[row]
        self.peer_label.setText(f"گفت‌وگو با: {self.current_peer['full_name']}")
        self.load_conversation()

    def _refresh_if_open(self):
        if self.current_peer and self.isVisible():
            self.load_conversation(mark_read=False)

    def load_conversation(self, mark_read=True):
        if not self.current_peer:
            return
        try:
            rows = api_client.chat_conversation(self.current_peer["id"])
        except ApiError:
            return
        while self.bubbles_lay.count() > 1:
            item = self.bubbles_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        my_id = getattr(api_client, "user_id", None)
        for m in rows:
            mine = (m["sender_id"] == my_id)
            b = Bubble(m["body"], mine, (m.get("created_at") or "")[:16].replace("T", " "))
            self.bubbles_lay.insertWidget(self.bubbles_lay.count() - 1, b)
        sb = self.scroll.verticalScrollBar()
        QTimer.singleShot(50, lambda: sb.setValue(sb.maximum()))

        
    def _send(self):

        from PySide6.QtWidgets import QMessageBox
        text = self.msg_input.text().strip()
        if not text:
            return
        if not self.current_peer:
            QMessageBox.information(self, "توجه", "ابتدا مخاطب را انتخاب کنید.")
            return
        try:
            api_client.chat_send(self.current_peer["id"], text)
        except ApiError as e:
            handle_api_error(self, e, "خطا در ارسال")
            return
        self.msg_input.clear()
        self.load_conversation()