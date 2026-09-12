from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QHBoxLayout, QMessageBox, QInputDialog, QLineEdit,
    QFileDialog, QComboBox, QHeaderView, QStackedWidget
)
from ui.chat_tab import ChatTab
from ui.client_requests_tab import ClientRequestsTab
from ui.follow_ups_tab import FollowUpsTab, NotificationsDialog
from PySide6.QtCore import Qt, QTimer
from ui.widgets import QuickFilterBar, MatchHighlightDelegate, bind_ctrl_f
from api_client import api_client, ApiError
from session import handle_api_error
from ui.property_form import PropertyFormDialog, DEAL_TYPE_LABELS
from ui.import_excel_dialog import ImportExcelDialog
from ui.user_form_dialog import UserFormDialog, ROLE_LABELS
from ui.property_filter_panel import PropertyFilterPanel
from PySide6.QtGui import QPixmap
from ui.property_gallery_dialog import PropertyGalleryDialog
from ui.dashboard_tab import DashboardTab
from ui.deals_tab import DealsTab
from ui.archive_tab import ArchiveTab
from ui.agent_center_tab import AgentCenterTab

class PropertyListTab(QWidget):
    """فهرست فایل‌ها — برای مشاور فقط فایل‌های خودش، برای مدیر همه (فیلتر در سرور اعمال می‌شود)."""

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._properties_by_row = []  # برای پیدا کردن دیتای کامل هنگام دابل‌کلیک برای ویرایش
        self._current_filters = {}  # آخرین فیلتری که اعمال شده (برای استفاده در export هم)
        self._current_page = 1
        self._total_pages = 1

        self.filter_panel = PropertyFilterPanel(on_apply=self._handle_apply_filters, on_clear=self._handle_clear_filters)



        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["عکس", "شهر", "نوع معامله", "متراژ", "اتاق", "آدرس", "تاریخ پایان قرارداد"]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)

        header.setSectionResizeMode(5, QHeaderView.Stretch)   # آدرس حالا ستون ۵ است
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 64)
        self.table.verticalHeader().setDefaultSectionSize(56)


        self.quick_bar = QuickFilterBar()
        self.quick_bar.filter_selected.connect(self._handle_quick_filter)

        self._delegate = MatchHighlightDelegate(self.table)
        self.table.setItemDelegate(self._delegate)

        bind_ctrl_f(self, self.filter_panel.search_input)

        add_btn = QPushButton("افزودن فایل جدید")
        add_btn.clicked.connect(self.handle_add_new)

        edit_btn = QPushButton("ویرایش فایل انتخاب‌شده")
        edit_btn.clicked.connect(self.handle_edit_selected)



        deactivate_btn = QPushButton("غیرفعال کردن فایل انتخاب‌شده")
        deactivate_btn.clicked.connect(self.handle_deactivate_selected)

        import_btn = QPushButton("ایمپورت از اکسل")
        import_btn.clicked.connect(self.handle_import_excel)

        export_pdf_btn = QPushButton("خروجی PDF")
        export_pdf_btn.clicked.connect(self.handle_export_pdf)

        export_excel_btn = QPushButton("خروجی اکسل")
        export_excel_btn.clicked.connect(self.handle_export_excel)

        # archive_btn = QPushButton("آرشیو فایل‌های غیرفعال")
        # archive_btn.clicked.connect(self.handle_open_archive)

        refresh_btn = QPushButton("به‌روزرسانی فهرست")
        refresh_btn.clicked.connect(self.load_properties)

        top_bar = QHBoxLayout()
        top_bar.addWidget(add_btn)
        top_bar.addWidget(edit_btn)
        top_bar.addWidget(deactivate_btn)
        top_bar.addWidget(import_btn)
        top_bar.addWidget(export_pdf_btn)
        top_bar.addWidget(export_excel_btn)
        # top_bar.addWidget(archive_btn)
        top_bar.addStretch()
        top_bar.addWidget(refresh_btn)
        view_img_btn = QPushButton("پیش‌نمایش عکس")
        view_img_btn.clicked.connect(self.handle_view_images)
        top_bar.addWidget(view_img_btn)

        # --- نوار صفحه‌بندی: بدون این، فایل‌های بعد از یک تعداد مشخص بی‌صدا از دید پنهان می‌ماندند ---
        self.prev_page_btn = QPushButton("◀ صفحه‌ی قبل")
        self.prev_page_btn.clicked.connect(self.handle_prev_page)
        self.next_page_btn = QPushButton("صفحه‌ی بعد ▶")
        self.next_page_btn.clicked.connect(self.handle_next_page)
        self.page_status_label = QLabel("")
        self.page_status_label.setAlignment(Qt.AlignCenter)

        pagination_bar = QHBoxLayout()
        pagination_bar.addWidget(self.prev_page_btn)
        pagination_bar.addStretch()
        pagination_bar.addWidget(self.page_status_label)
        pagination_bar.addStretch()
        pagination_bar.addWidget(self.next_page_btn)


        self.toggle_filter_btn = QPushButton("پنهان کردن فیلترها ▲")
        self.toggle_filter_btn.setObjectName("chip")
        self.toggle_filter_btn.clicked.connect(self._toggle_filters)

        tools_row = QHBoxLayout()
        tools_row.addWidget(self.toggle_filter_btn)
        tools_row.addWidget(self.quick_bar, 1)

        layout = QVBoxLayout()
        layout.addLayout(tools_row)
        layout.addWidget(self.filter_panel)
        layout.addLayout(top_bar)
        layout.addWidget(self.table)
        layout.addLayout(pagination_bar)
        self.setLayout(layout)

        self.load_properties()

    def _toggle_filters(self):
        show = not self.filter_panel.isVisible()
        self.filter_panel.setVisible(show)
        self.toggle_filter_btn.setText("پنهان کردن فیلترها ▲" if show else "نمایش فیلترها ▼")

    def _handle_apply_filters(self, filters: dict):
        self._current_filters = filters
        self._current_page = 1
        self.load_properties()

    def _handle_clear_filters(self):
        self._current_filters = {}
        self._current_page = 1
        self.load_properties()

    def handle_prev_page(self):
        if self._current_page > 1:
            self._current_page -= 1
            self.load_properties()

    def handle_next_page(self):
        if self._current_page < self._total_pages:
            self._current_page += 1
            self.load_properties()

    def load_properties(self):
        try:
            response = api_client.list_properties(page=self._current_page, **self._current_filters)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return

        properties = response["items"]
        self._total_pages = response["total_pages"]
        # اگر با تغییر فیلتر صفحه‌ی فعلی از تعداد صفحات جدید بیشتر شد، به آخرین صفحه‌ی معتبر برگرد
        if self._current_page > self._total_pages:
            self._current_page = self._total_pages
            if properties == [] and self._total_pages >= 1:
                self.load_properties()
                return

        self.page_status_label.setText(
            f"صفحه {self._current_page} از {self._total_pages} — تعداد کل: {response['total']}"
        )
        self.prev_page_btn.setEnabled(self._current_page > 1)
        self.next_page_btn.setEnabled(self._current_page < self._total_pages)

        self._properties_by_row = properties
        self._delegate.set_term(self.filter_panel.search_input.text())
        self.table.setRowCount(len(properties))
        for row, p in enumerate(properties):
            item0 = QTableWidgetItem()
            if p.get("cover_image_id"):
                pm = self._get_thumb(p["id"], p["cover_image_id"])
                if pm:
                    item0.setData(Qt.DecorationRole, pm)
            self.table.setItem(row, 0, item0)
            self.table.setItem(row, 1, QTableWidgetItem(p.get("city", "")))
            self.table.setItem(row, 2, QTableWidgetItem(DEAL_TYPE_LABELS.get(p.get("deal_type"), "")))
            self.table.setItem(row, 3, QTableWidgetItem(str(p.get("area_m2") or "")))
            self.table.setItem(row, 4, QTableWidgetItem(str(p.get("rooms") or "")))
            self.table.setItem(row, 5, QTableWidgetItem(p.get("address") or ""))
            self.table.setItem(row, 6, QTableWidgetItem(p.get("contract_end_date") or ""))



    def _get_thumb(self, prop_id, image_id):
        if not hasattr(self, "_pix_cache"):
            self._pix_cache = {}
        if image_id in self._pix_cache:
            return self._pix_cache[image_id]
        try:
            data = api_client.get_property_image_bytes(prop_id, image_id)
        except ApiError:
            return None
        pm = QPixmap()
        pm.loadFromData(data)
        pm = pm.scaled(52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._pix_cache[image_id] = pm
        return pm

    def handle_view_images(self):
        prop = self._selected_property()
        if not prop:
            QMessageBox.information(self, "توجه", "ابتدا یک فایل انتخاب کنید.")
            return
        if not prop.get("has_images"):
            QMessageBox.information(self, "توجه", "این فایل عکس ندارد.")
            return
        PropertyGalleryDialog(prop["id"],
                              property_label=prop.get("address") or prop.get("city") or "").exec()
        

    def _selected_property(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._properties_by_row):
            return None
        return self._properties_by_row[row]

    def handle_add_new(self):
        dialog = PropertyFormDialog(property_data=None, on_saved=self.load_properties)
        dialog.exec()

    def handle_edit_selected(self):
        prop = self._selected_property()
        if not prop:
            QMessageBox.information(self, "توجه", "ابتدا یک فایل را از فهرست انتخاب کنید.")
            return
        dialog = PropertyFormDialog(property_data=prop, on_saved=self.load_properties)
        dialog.exec()

    def handle_deactivate_selected(self):
        prop = self._selected_property()
        if not prop:
            QMessageBox.information(self, "توجه", "ابتدا یک فایل را از فهرست انتخاب کنید.")
            return
        confirm = QMessageBox.question(
            self, "تایید", f"فایل «{prop.get('address') or prop.get('city')}» غیرفعال شود؟"
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            api_client.deactivate_property(prop["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.load_properties()

    def handle_import_excel(self):
        dialog = ImportExcelDialog(on_imported=self.load_properties)
        dialog.exec()

    def handle_export_pdf(self):
        save_path, _ = QFileDialog.getSaveFileName(self, "ذخیره‌ی PDF", "فهرست-فایل-ها.pdf", "PDF Files (*.pdf)")
        if not save_path:
            return
        try:
            api_client.export_properties_pdf(save_path, **self._current_filters)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        QMessageBox.information(self, "موفق", f"فایل PDF ذخیره شد:\n{save_path}")

    def handle_export_excel(self):
        save_path, _ = QFileDialog.getSaveFileName(
            self, "ذخیره‌ی اکسل", "فهرست-فایل-ها.xlsx", "Excel Files (*.xlsx)"
        )
        if not save_path:
            return
        try:
            api_client.export_properties_excel(save_path, **self._current_filters)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        QMessageBox.information(self, "موفق", f"فایل اکسل ذخیره شد:\n{save_path}")

    # def handle_open_archive(self):
    #     dialog = ArchivePropertiesDialog(on_restored=self.load_properties)
    #     dialog.exec()

    def _handle_quick_filter(self, key, value):
        fp = self.filter_panel
        if key is None:                      # چیپ «همه»
            fp._handle_clear()
            return
        if key == "deal_type":
            idx = fp.deal_type_combo.findData(value)
            fp.deal_type_combo.setCurrentIndex(max(idx, 0))
        elif key == "max_price_sale":
            fp.deal_type_combo.setCurrentIndex(fp.deal_type_combo.findData("sale"))
            fp.min_price_input.clear()
            fp.max_price_input.set_value(value)
        elif key == "min_area":
            fp.max_area_input.setValue(0)
            fp.min_area_input.setValue(value)
        elif key == "has_elevator":
            fp.elevator_combo.setCurrentIndex(2)
        elif key == "has_parking":
            fp.parking_combo.setCurrentIndex(2)
        fp._handle_apply()


class RenewalsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._items = []
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["شهر", "آدرس", "نام مالک", "تاریخ پایان قرارداد", "تلفن مالک"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._on_cell_double_click)
        hint = QLabel("برای پیگیری و ویرایش فایل، روی ردیف دابل‌کلیک کنید.")
        refresh_btn = QPushButton("به‌روزرسانی")
        refresh_btn.clicked.connect(self.load_renewals)
        bar = QHBoxLayout()
        bar.addWidget(hint)
        bar.addStretch()
        bar.addWidget(refresh_btn)

        layout = QVBoxLayout()
        layout.addLayout(bar)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.load_renewals()


    def _on_cell_double_click(self, row, column):
        if 0 <= row < len(self._items):
            PropertyFormDialog(property_data=self._items[row], on_saved=self.load_renewals).exec()



    def load_renewals(self):
        try:
            self._items = api_client.upcoming_renewals(days=30)
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        self.table.setRowCount(len(self._items))
        for row, p in enumerate(self._items):
            self.table.setItem(row, 0, QTableWidgetItem(p.get("city", "")))
            self.table.setItem(row, 1, QTableWidgetItem(p.get("address") or ""))
            self.table.setItem(row, 2, QTableWidgetItem(p.get("owner_name") or ""))
            self.table.setItem(row, 3, QTableWidgetItem(p.get("contract_end_date") or ""))
            self.table.setItem(row, 4, QTableWidgetItem(p.get("owner_phone") or ""))

    def _open_selected(self):
        row = self.table.currentRow()
        if 0 <= row < len(self._items):
            PropertyFormDialog(property_data=self._items[row], on_saved=self.load_renewals).exec()



class ActivityLogTab(QWidget):
    """فقط برای مدیر: تاریخچه‌ی کامل عملیات (چه کسی، چه زمانی، چه کاری)."""

    ENTITY_TYPE_LABELS = {"": "همه", "property": "فایل ملکی", "user": "کاربر"}
    ACTION_LABELS = {
        "create": "ثبت", "update": "ویرایش", "deactivate": "غیرفعال‌سازی", "activate": "فعال‌سازی",
        "reactivate": "بازگردانی", "reset_password": "ریست رمز", "login": "ورود",
        "import_excel": "ایمپورت اکسل", "upload_image": "آپلود عکس", "delete_image": "حذف عکس",
    }

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._current_page = 1
        self._total_pages = 1

        self.entity_filter_combo = QComboBox()
        for value, label in self.ENTITY_TYPE_LABELS.items():
            self.entity_filter_combo.addItem(label, value)
        self.entity_filter_combo.currentIndexChanged.connect(self._handle_filter_changed)

        self.days_filter_combo = QComboBox()
        for value, label in [(7, "۷ روز اخیر"), (30, "۳۰ روز اخیر"), (90, "۹۰ روز اخیر"), (0, "همه‌ی تاریخچه")]:
            self.days_filter_combo.addItem(label, value)
        self.days_filter_combo.setCurrentIndex(1)  # پیش‌فرض: ۳۰ روز اخیر
        self.days_filter_combo.currentIndexChanged.connect(self._handle_filter_changed)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["زمان", "کاربر", "عملیات", "نوع", "جزئیات"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        refresh_btn = QPushButton("به‌روزرسانی")
        refresh_btn.clicked.connect(self.load_logs)

        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("نوع:"))
        filter_bar.addWidget(self.entity_filter_combo)
        filter_bar.addWidget(QLabel("بازه:"))
        filter_bar.addWidget(self.days_filter_combo)
        filter_bar.addStretch()
        filter_bar.addWidget(refresh_btn)

        self.prev_btn = QPushButton("◀ صفحه‌ی قبل")
        self.prev_btn.clicked.connect(self.handle_prev_page)
        self.next_btn = QPushButton("صفحه‌ی بعد ▶")
        self.next_btn.clicked.connect(self.handle_next_page)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)

        pagination_bar = QHBoxLayout()
        pagination_bar.addWidget(self.prev_btn)
        pagination_bar.addStretch()
        pagination_bar.addWidget(self.status_label)
        pagination_bar.addStretch()
        pagination_bar.addWidget(self.next_btn)

        layout = QVBoxLayout()
        layout.addLayout(filter_bar)
        layout.addWidget(self.table)
        layout.addLayout(pagination_bar)
        self.setLayout(layout)

        self.load_logs()

    def _handle_filter_changed(self):
        self._current_page = 1
        self.load_logs()

    def load_logs(self):
        try:
            response = api_client.list_activity_logs(
                page=self._current_page,
                entity_type=self.entity_filter_combo.currentData() or None,
                days=self.days_filter_combo.currentData(),
            )
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return

        logs = response["items"]
        self._total_pages = response["total_pages"]

        self.table.setRowCount(len(logs))
        for row, log in enumerate(logs):
            self.table.setItem(row, 0, QTableWidgetItem(log["created_at"].replace("T", " ")[:19]))
            self.table.setItem(row, 1, QTableWidgetItem(log.get("user_full_name") or log.get("username") or ""))
            self.table.setItem(row, 2, QTableWidgetItem(self.ACTION_LABELS.get(log["action"], log["action"])))
            self.table.setItem(row, 3, QTableWidgetItem(self.ENTITY_TYPE_LABELS.get(log["entity_type"], log["entity_type"])))
            self.table.setItem(row, 4, QTableWidgetItem(log.get("detail") or ""))

        self.status_label.setText(
            f"صفحه {self._current_page} از {self._total_pages} — تعداد کل: {response['total']}"
        )
        self.prev_btn.setEnabled(self._current_page > 1)
        self.next_btn.setEnabled(self._current_page < self._total_pages)

    def handle_prev_page(self):
        if self._current_page > 1:
            self._current_page -= 1
            self.load_logs()

    def handle_next_page(self):
        if self._current_page < self._total_pages:
            self._current_page += 1
            self.load_logs()



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle(f"سامانه‌ی مدیریت فایل‌های ملکی — {api_client.full_name}")
        self.resize(1150, 720)

        # --- زنگ اطلاع‌یه (بالای سایدبار) ---
        self._bell_btn = QPushButton("🔔 اطلاع‌یه‌ها")
        self._bell_btn.setObjectName("bellLabel")
        self._bell_btn.setCursor(Qt.PointingHandCursor)
        self._bell_btn.clicked.connect(self._open_notifications)

        # --- سایدبار + صفحه‌ها ---
        self._sidebar = QListWidget()
        self._sidebar.setObjectName("sideNav")
        self._sidebar.setFixedWidth(210)
        self._stack = QStackedWidget()
        self._index = {}

        side_title = QLabel("ملک‌یار")
        side_title.setObjectName("sideTitle")
        side_title.setAlignment(Qt.AlignCenter)

        self._list_tab = PropertyListTab()
        pages = [
            ("🏠  داشبورد", DashboardTab(on_navigate=self._dashboard_navigate), "dashboard"),
            ("🏢  فهرست فایل‌ها", self._list_tab, "list"),
            ("📅  قراردادهای رو‌به‌اتمام", RenewalsTab(), "renewals"),
            ("🗄️  بایگانی", ArchiveTab(), "archive"),
            ("🙋  درخواست مشتری‌ها", ClientRequestsTab(), "requests"),
            ("✅  پیگیری روزمره", FollowUpsTab(), "followups"),
        ]
        if api_client.role == "admin":
            pages += [
                ("👥  مشاوران و مدیریت", AgentCenterTab(), "agents"),
                ("💰  حسابداری پورسانت", DealsTab(), "deals"),
                ("🕘  تاریخچه‌ی فعالیت‌ها", ActivityLogTab(), "activity"),
            ]

        for label, widget, key in pages:
            self._stack.addWidget(widget)
            self._sidebar.addItem(label)
            self._index[key] = self._sidebar.count() - 1

        self._sidebar.currentRowChanged.connect(self._stack.setCurrentIndex)
        self._sidebar.setCurrentRow(self._index["dashboard"])
        self._renewals_tab_index = self._index["renewals"]  # سازگاری با main.py

        side_lay = QVBoxLayout()
        side_lay.setContentsMargins(0, 8, 0, 8)
        side_lay.addWidget(side_title)
        side_lay.addWidget(self._bell_btn)
        side_lay.addWidget(self._sidebar, 1)

        central = QWidget()
        lay = QHBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addLayout(side_lay)
        lay.addWidget(self._stack, 1)
        self.setCentralWidget(central)

        self._notif_timer = QTimer(self)
        self._notif_timer.timeout.connect(self._refresh_bell)
        self._notif_timer.start(60_000)
        QTimer.singleShot(800, self._refresh_bell)

    def switch_to_renewals_tab(self):
        self._sidebar.setCurrentRow(self._index["renewals"])

    def _dashboard_navigate(self, target, deal_type=None):
        if target == "list":
            if deal_type:
                fp = self._list_tab.filter_panel
                fp.deal_type_combo.setCurrentIndex(fp.deal_type_combo.findData(deal_type))
                self._list_tab._handle_apply_filters(fp.get_filters())
            self._sidebar.setCurrentRow(self._index["list"])
        elif target in self._index:
            self._sidebar.setCurrentRow(self._index[target])

    def _refresh_bell(self):
        try:
            n = api_client.unread_count().get("unread", 0)
        except ApiError:
            n = 0
        try:
            c = api_client.chat_unread_total().get("unread", 0)
        except ApiError:
            c = 0
        self._bell_btn.setText(f"🔔 ({n + c})" if (n or c) else "🔔 اطلاع‌یه‌ها")

    def _open_notifications(self):
        NotificationsDialog(on_changed=self._refresh_bell).exec()
        self._refresh_bell()