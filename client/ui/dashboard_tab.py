from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QFrame, QPushButton, QHBoxLayout

from api_client import api_client, ApiError
from session import handle_api_error


class StatCard(QFrame):
    clicked = Signal()   # ← این خط را جا انداخته بودی

    def __init__(self, title: str, color: str = "#8b94ff"):
        super().__init__()
        self.setObjectName("statCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)

        self.value_label = QLabel("—")
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet(
            f"font-size: 26px; font-weight: bold; color: {color};"
            "background: transparent; border: none;"
        )

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(
            "font-size: 12px; color: rgba(232,236,248,0.65);"
            "background: transparent; border: none;"
        )

        layout = QVBoxLayout()
        layout.addWidget(self.value_label)
        layout.addWidget(title_label)
        self.setLayout(layout)

    def set_value(self, value):
        self.value_label.setText(str(value))

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class DashboardTab(QWidget):
    def __init__(self, on_navigate=None):   # ← پارامتر باید همین‌جا باشد
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._on_navigate = on_navigate

        self.total_card = StatCard("کل فایل‌های فعال", color="#8b94ff")
        self.sale_card = StatCard("فروش", color="#7dd3fc")
        self.presale_card = StatCard("پیش‌خرید", color="#c4b5fd")
        self.rent_card = StatCard("اجاره", color="#86efac")
        self.mortgage_card = StatCard("رهن کامل", color="#fcd34d")
        self.new_week_card = StatCard("فایل جدید این هفته", color="#6ee7b7")
        self.urgent_card = StatCard("قرارداد فوری (زیر ۷ روز)", color="#fca5a5")
        self.upcoming_card = StatCard("قرارداد رو‌به‌اتمام (زیر ۳۰ روز)", color="#fdba74")
        self.agents_card = StatCard("تعداد مشاوران", color="#a5b4fc")
        self.activity_today_card = StatCard("فعالیت امروز", color="#93c5fd")

        role_fa = "مدیر" if api_client.role == "admin" else "مشاور"
        welcome = QLabel(f"👋 خوش آمدید، {api_client.full_name} ({role_fa})")
        welcome.setStyleSheet("font-size: 14px; font-weight: bold; color: #a5b4fc; background: transparent;")

        self.total_card.clicked.connect(lambda: self._go("list"))
        self.sale_card.clicked.connect(lambda: self._go("list", "sale"))
        self.presale_card.clicked.connect(lambda: self._go("list", "presale"))
        self.rent_card.clicked.connect(lambda: self._go("list", "rent"))
        self.mortgage_card.clicked.connect(lambda: self._go("list", "mortgage"))
        self.urgent_card.clicked.connect(lambda: self._go("renewals"))
        self.upcoming_card.clicked.connect(lambda: self._go("renewals"))
        if api_client.role == "admin":
            self.agents_card.clicked.connect(lambda: self._go("agents"))
            self.activity_today_card.clicked.connect(lambda: self._go("activity"))

        grid = QGridLayout()
        grid.addWidget(self.total_card, 0, 0)
        grid.addWidget(self.sale_card, 0, 1)
        grid.addWidget(self.presale_card, 0, 2)
        grid.addWidget(self.rent_card, 0, 3)
        grid.addWidget(self.mortgage_card, 0, 4)
        grid.addWidget(self.new_week_card, 1, 0)
        grid.addWidget(self.urgent_card, 1, 1)
        grid.addWidget(self.upcoming_card, 1, 2)
        if api_client.role == "admin":
            grid.addWidget(self.agents_card, 1, 3)
            grid.addWidget(self.activity_today_card, 1, 4)

        refresh_btn = QPushButton("به‌روزرسانی")
        refresh_btn.clicked.connect(self.load_summary)
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        top_bar.addWidget(refresh_btn)

        layout = QVBoxLayout()
        layout.addWidget(welcome)
        layout.addLayout(top_bar)
        layout.addLayout(grid)
        layout.addStretch()
        self.setLayout(layout)

        self.load_summary()

    def load_summary(self):
        try:
            data = api_client.get_dashboard_summary()
        except ApiError as e:
            handle_api_error(self, e, "خطا در بارگذاری داشبورد")
            return

        self.total_card.set_value(data["total_active"])
        by_type = data.get("by_deal_type", {})
        self.sale_card.set_value(by_type.get("sale", 0))
        self.presale_card.set_value(by_type.get("presale", 0))
        self.rent_card.set_value(by_type.get("rent", 0))
        self.mortgage_card.set_value(by_type.get("mortgage", 0))
        self.new_week_card.set_value(data.get("new_this_week", 0))
        self.urgent_card.set_value(data.get("urgent_renewals", 0))
        self.upcoming_card.set_value(data.get("upcoming_renewals", 0))

        if "total_agents" in data:
            self.agents_card.set_value(data["total_agents"])
        if "activity_today" in data:
            self.activity_today_card.set_value(data["activity_today"])

    def _go(self, target, deal_type=None):
        if self._on_navigate:
            self._on_navigate(target, deal_type)