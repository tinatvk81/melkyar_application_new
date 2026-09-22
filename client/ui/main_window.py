from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QHBoxLayout, QMessageBox, QInputDialog, QLineEdit,
    QFileDialog, QComboBox, QHeaderView, QStackedWidget, QFrame, QAbstractItemView
)
from collections import Counter
from PySide6.QtCore import Signal
from ui.global_search import GlobalSearchDialog
import webbrowser
from urllib.parse import quote as _urlquote
from PySide6.QtWidgets import QMenu
from ui.spinner import TableSpinner
import math
from ui.jalali_util import to_jalali_str
from ui.my_ledger_tab import MyLedgerTab
from PySide6.QtWidgets import QApplication
from ui.styles import apply_persian_rtl_style
import settings_manager
from ui.property_card_view import PropertyCardView
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
from ui.property_gallery_dialog import PropertyGalleryDialog
from ui.dashboard_tab import DashboardTab
from ui.deals_tab import DealsTab
from PySide6.QtGui import QKeySequence, QShortcut, QColor, QPixmap
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
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            ["عکس", "شهر", "نوع معامله", "قیمت", "متری", "متراژ", "اتاق", "آدرس", "تاریخ پایان قرارداد"]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)

        header.setSectionResizeMode(8, QHeaderView.Stretch)   # آدرس حالا ستون ۸ است
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 64)
        self.table.verticalHeader().setDefaultSectionSize(56)

        # --- نمای کارتی (دیوارگونه) ---
        self.card_view = PropertyCardView(thumb_loader=self._get_thumb, on_open=self._open_property_card)
        self.card_view.setVisible(False)

        
        self.quick_bar = QuickFilterBar()
        self.quick_bar.preset_selected.connect(self._handle_preset_filter)

        self._delegate = MatchHighlightDelegate(self.table)
        self.table.setItemDelegate(self._delegate)

        bind_ctrl_f(self, self.filter_panel.search_input)

        add_btn = QPushButton("افزودن فایل جدید")
        add_btn.clicked.connect(self.handle_add_new)

        edit_btn = QPushButton("ویرایش فایل انتخاب‌شده")
        edit_btn.clicked.connect(self.handle_edit_selected)

        if api_client.role == "admin":
            self.delete_btn = QPushButton("🗑 حذف فایل")
            self.delete_btn.setToolTip("حذف نرم — فقط مدیر؛ با تأیید تایپی")
            self.delete_btn.clicked.connect(self.handle_delete_selected)


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

        self.contact_btn = QPushButton("📞 تماس / واتساپ")
        self.contact_btn.setToolTip("کپی شماره، واتساپ مالک، یا باز کردن نقشه‌ی آدرس فایل انتخاب‌شده")
        self.contact_btn.clicked.connect(self._show_contact_menu)


        top_bar = QHBoxLayout()
        top_bar.addWidget(add_btn)
        top_bar.addWidget(edit_btn)
        if api_client.role == "admin":
            top_bar.addWidget(self.delete_btn)
        top_bar.addWidget(deactivate_btn)
        top_bar.addWidget(import_btn)
        top_bar.addWidget(self.contact_btn)
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
        self.view_toggle_btn = QPushButton("نمایش کارتی 🖼")
        self.view_toggle_btn.setObjectName("chip")
        self.view_toggle_btn.clicked.connect(self._toggle_view)
        self.urgent_filter_btn = QPushButton("🔥 فوری‌ها")
        self.urgent_filter_btn.setObjectName("chip")
        self.urgent_filter_btn.setCheckable(True)
        self.urgent_filter_btn.setToolTip("فقط فایل‌های فوری: تاریخ فوری رد نشده یا قرارداد زیر ۷ روز")
        self.urgent_filter_btn.toggled.connect(self._toggle_urgent_filter)

        tools_row = QHBoxLayout()
        tools_row.addWidget(self.toggle_filter_btn)
        tools_row.addWidget(self.quick_bar, 1)
        tools_row.addWidget(self.urgent_filter_btn)
        tools_row.addWidget(self.view_toggle_btn)

        layout = QVBoxLayout()
        layout.addLayout(tools_row)
        layout.addWidget(self.filter_panel)
        layout.addLayout(top_bar)
        layout.addWidget(self.table)
        layout.addWidget(self.card_view)
        layout.addLayout(pagination_bar)
        self.setLayout(layout)

        self.load_properties()

    def _toggle_filters(self):
        show = not self.filter_panel.isVisible()
        self.filter_panel.setVisible(show)
        self.toggle_filter_btn.setText("پنهان کردن فیلترها ▲" if show else "نمایش فیلترها ▼")

    def _reload_all(self):
        self.load_properties()
        if self.card_view.isVisible():
            self.card_view.load(**self._current_filters)

    def _toggle_urgent_filter(self, checked: bool):
        if checked:
            self._current_filters["urgent_only"] = True
        else:
            self._current_filters.pop("urgent_only", None)
        self._current_page = 1
        self.load_properties()
        if self.card_view.isVisible():
            self.card_view.load(**self._current_filters)

    def _handle_apply_filters(self, filters: dict):
        keep_urgent = self._current_filters.get("urgent_only")
        self._current_filters = filters
        if keep_urgent:
            self._current_filters["urgent_only"] = True
        self._current_page = 1
        self.load_properties()
        if self.card_view.isVisible(): self.card_view.load(**self._current_filters)


    def _toggle_view(self):
        card_mode = not self.card_view.isVisible()
        self.card_view.setVisible(card_mode)
        self.table.setVisible(not card_mode)
        self.view_toggle_btn.setText("نمای جدول 📋" if card_mode else "نمایش کارتی 🖼")
        if card_mode:
            self.card_view.load(**self._current_filters)



    def _handle_clear_filters(self):
        self._current_filters = {}
        self._current_page = 1
        self.load_properties()
        if self.card_view.isVisible(): self.card_view.load(**self._current_filters)

    def handle_prev_page(self):
        if self._current_page > 1:
            self._current_page -= 1
            self.load_properties()

    def handle_next_page(self):
        if self._current_page < self._total_pages:
            self._current_page += 1
            self.load_properties()

    def load_properties(self):
        TableSpinner.show(self.table)
        try:
            response = api_client.list_properties(page=self._current_page, **self._current_filters)
        except ApiError as e:
            TableSpinner.hide(self.table)
            handle_api_error(self, e, "خطا")
            return
        TableSpinner.hide(self.table)

        properties = response["items"]
        self._total_pages = response["total_pages"]
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
            dt_txt = DEAL_TYPE_LABELS.get(p.get("deal_type"), "")
            if p.get("urgent_until"):
                dt_txt += "  🔥"
            if p.get("convertible_note"):
                dt_txt += "  🔁"
            self.table.setItem(row, 2, QTableWidgetItem(dt_txt))
            price_item = QTableWidgetItem(p.get("price_display") or "—")
            _pf = price_item.font(); _pf.setBold(True); price_item.setFont(_pf)
            self.table.setItem(row, 3, price_item)
            self.table.setItem(row, 4, QTableWidgetItem(p.get("price_per_m2_display") or "—"))
            _a = p.get("area_m2")
            _a_txt = f"{_a:g}" if _a else ""
            self.table.setItem(row, 5, QTableWidgetItem(_a_txt))
            self.table.setItem(row, 6, QTableWidgetItem(str(p.get("rooms") or "")))
            addr_item = QTableWidgetItem(p.get("address") or "")
            if p.get("convertible_note"):
                addr_item.setToolTip(f"🔁 قابل تبدیل: {p['convertible_note']}")
            self.table.setItem(row, 7, addr_item)
            self.table.setItem(row, 8, QTableWidgetItem(to_jalali_str(p.get("contract_end_date"))))

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
        
    def _show_contact_menu(self):
        prop = self._selected_property()
        if not prop:
            QMessageBox.information(self, "توجه", "ابتدا یک فایل انتخاب کنید.")
            return
        phone = (prop.get("owner_phone") or "").strip()
        addr = (prop.get("address") or "").strip()
        city = (prop.get("city") or "").strip()

        intl = None
        menu = QMenu(self)
        act_copy = act_wa = act_map = None
        if phone:
            act_copy = menu.addAction(f"📋 کپی شماره مالک ({phone})")
            digits = phone.replace("+98", "0")
            if len(digits) >= 10:
                intl = "98" + digits.lstrip("0")[-10:]
                act_wa = menu.addAction(f"📲 واتساپ مالک (+{intl})")
        if city:
            act_map = menu.addAction("🗺 باز کردن آدرس در نقشه‌ی گوگل")
        if not (act_copy or act_wa or act_map):
            QMessageBox.information(self, "توجه", "این فایل تلفن/آدرسی ثبت نکرده است.")
            return
        chosen = menu.exec(self.contact_btn.mapToGlobal(self.contact_btn.rect().topLeft()))
        if chosen is None:
            return
        if chosen == act_copy and phone:
            QApplication.clipboard().setText(phone)
            from ui.toast import Toast
            Toast.show("📋 شماره کپی شد")
        elif chosen == act_wa and intl:
            webbrowser.open(f"https://wa.me/{intl}")
        elif chosen == act_map and city:
            q = _urlquote(f"{city} {addr}")
            webbrowser.open(f"https://www.google.com/maps/search/?api=1&query={q}")


    def _selected_property(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._properties_by_row):
            return None
        return self._properties_by_row[row]

    def handle_add_new(self):
        dialog = PropertyFormDialog(property_data=None, on_saved=self._reload_all)
        dialog.exec()

    def handle_edit_selected(self):
        prop = self._selected_property()
        if not prop:
            QMessageBox.information(self, "توجه", "ابتدا یک فایل را از فهرست انتخاب کنید.")
            return
        dialog = PropertyFormDialog(property_data=prop, on_saved=self._reload_all)
        dialog.exec()

    def _open_property_card(self, prop):
        PropertyFormDialog(property_data=prop, on_saved=self._reload_all).exec()
        

    def handle_delete_selected(self):
        if api_client.role != "admin":
            return
        prop = self._selected_property()
        if not prop:
            QMessageBox.information(self, "توجه", "ابتدا یک فایل انتخاب کنید.")
            return
        label = prop.get("address") or prop.get("city") or f"#{prop['id']}"
        QMessageBox.warning(
            self, "حذف فایل",
            f"⚠️ این عمل فایل «{label}» را از همهٔ فهرست‌ها و جست‌وجوها حذف می‌کند.\n"
            "رکورد در دیتابیس می‌ماند و فقط با کمک پشتیبانی قابل بازگردانی است.")
        text, ok = QInputDialog.getText(
            self, "تأیید حذف",
            f"برای تأیید حذف فایل #{prop['id']}، کلمهٔ «حذف» را دقیقاً تایپ کن:")
        if not ok or text.strip() != "حذف":
            return
        try:
            api_client.soft_delete_property(prop["id"])
        except ApiError as e:
            handle_api_error(self, e, "خطا در حذف")
            return
        from ui.toast import Toast
        Toast.show("🗑 فایل حذف شد")
        self._reload_all()

        
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

    def _handle_preset_filter(self, params: dict):
        if not params:                      # چیپ «همه» → پاک‌سازی
            self._handle_clear_filters()
            return
        self._handle_apply_filters(params)


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
            self.table.setItem(row, 3, QTableWidgetItem(to_jalali_str(p.get("contract_end_date"))))
            self.table.setItem(row, 4, QTableWidgetItem(p.get("owner_phone") or ""))

    def _open_selected(self):
        row = self.table.currentRow()
        if 0 <= row < len(self._items):
            PropertyFormDialog(property_data=self._items[row], on_saved=self.load_renewals).exec()



class _StatCard(QFrame):
    """کارت آمار قابل‌کلیک برای فیلتر عملیات."""
    clicked = Signal()

    def __init__(self, title, color):
        super().__init__()
        self.setObjectName("statCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(150, 74)
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 10, 8, 10)
        self.value_label = QLabel("0")
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet(
            f"font-size: 20px; font-weight: 800; color: {color}; background: transparent; border: none;")
        t = QLabel(title)
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("font-size: 11px; color: rgba(232,236,248,0.65); background: transparent; border: none;")
        v.addWidget(self.value_label)
        v.addWidget(t)

    def mousePressEvent(self, e):
        self.clicked.emit()
        super().mousePressEvent(e)


class ActivityLogTab(QWidget):
    """فقط برای مدیر: تاریخچهٔ کامل عملیات — با کارت‌های آماری و بج‌های رنگی."""

    ENTITY_TYPE_LABELS = {
        "": "همه", "property": "فایل ملکی", "user": "کاربر", "deal": "معامله",
        "deal_payment": "پرداخت", "client_request": "درخواست مشتری", "follow_up": "پیگیری",
    }
    ACTION_LABELS = {
        "create": "ثبت", "update": "ویرایش", "delete": "حذف",
        "deactivate": "غیرفعال‌سازی", "activate": "فعال‌سازی", "reactivate": "بازگردانی",
        "reset_password": "ریست رمز", "login": "ورود", "logout": "خروج",
        "import_excel": "ایمپورت اکسل", "upload_image": "آپلود عکس", "delete_image": "حذف عکس",
        "finalize": "قطعی‌کردن",
    }
    ACTION_COLORS = {
        "create": "#22c55e", "login": "#7dd3fc", "update": "#f5a623", "delete": "#ef4444",
        "deactivate": "#f87171", "activate": "#86efac", "reactivate": "#2dd4bf",
        "reset_password": "#c4b5fd", "import_excel": "#fdba74",
        "upload_image": "#86efac", "delete_image": "#f87171", "finalize": "#22c55e",
    }
    STAT_CARDS = [
        (None, "مجموع فعالیت‌ها", "#f5a623"),
        ("create", "ثبت", "#22c55e"),
        ("login", "ورود", "#7dd3fc"),
        ("update", "ویرایش", "#a5b4fc"),
        ("delete", "حذف", "#ef4444"),
    ]

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._current_page = 1
        self._total_pages = 1
        self._logs = []
        self._action_filter = None

        # --- کمبوها ---
        self.entity_filter_combo = QComboBox()
        for value, label in self.ENTITY_TYPE_LABELS.items():
            self.entity_filter_combo.addItem(label, value)
        self.entity_filter_combo.currentIndexChanged.connect(self._handle_filter_changed)

        self.user_filter_combo = QComboBox()
        self.user_filter_combo.addItem("همه کاربران", None)
        try:
            for u in api_client.list_users():
                self.user_filter_combo.addItem(u["full_name"], u["id"])
        except ApiError:
            pass
        self.user_filter_combo.currentIndexChanged.connect(self._handle_filter_changed)

        self.days_filter_combo = QComboBox()
        for value, label in [(7, "۷ روز اخیر"), (30, "۳۰ روز اخیر"), (90, "۹۰ روز اخیر"), (0, "همه‌ی تاریخچه")]:
            self.days_filter_combo.addItem(label, value)
        self.days_filter_combo.setCurrentIndex(1)
        self.days_filter_combo.currentIndexChanged.connect(self._handle_filter_changed)

        refresh_btn = QPushButton("به‌روزرسانی")
        refresh_btn.clicked.connect(self.load_logs)

        title = QLabel("🕘 تاریخچه‌ی فعالیت‌ها")
        title.setStyleSheet("font-size: 15px; font-weight: 800; color: #f5a623; background: transparent;")

        filter_bar = QHBoxLayout()
        filter_bar.addWidget(title)
        filter_bar.addSpacing(18)
        filter_bar.addWidget(QLabel("نوع:"));    filter_bar.addWidget(self.entity_filter_combo)
        filter_bar.addWidget(QLabel("کاربر:"));  filter_bar.addWidget(self.user_filter_combo)
        filter_bar.addWidget(QLabel("بازه:"));   filter_bar.addWidget(self.days_filter_combo)
        filter_bar.addStretch()
        filter_bar.addWidget(refresh_btn)

        # --- کارت‌های آماری (کلیک = فیلتر همان عملیات) ---
        self._stat_cards = {}
        self._action_filter = None
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)
        for key, title_c, color in self.STAT_CARDS:
            card = _StatCard(title_c, color)
            card.clicked.connect(lambda k=key: self._toggle_action_filter(k))
            self._stat_cards[key] = card
            stats_row.addWidget(card)
        stats_row.addStretch()

        # --- جدول دوستونی ---
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["عملیات", "کاربر", "زمان", "زمان", "کاربر", "عملیات"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(
            "QTableWidget::item { border-right: 1px solid rgba(128,128,140,0.35); }"
            "QTableWidget::item:selected { background: rgba(245,166,35,0.25); }")

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
        layout.addLayout(stats_row)
        layout.addWidget(self.table)
        layout.addLayout(pagination_bar)
        self.setLayout(layout)

        self.load_logs()

    # ---------- آمار و فیلتر عملیات ----------
    def _toggle_action_filter(self, key):
        self._action_filter = None if self._action_filter == key else key
        self._refresh_card_selection()
        self._render()

    def _refresh_card_selection(self):
        for key, card in self._stat_cards.items():
            if key == self._action_filter:
                card.setStyleSheet("QFrame#statCard { border: 1px solid #f5a623; }")
            else:
                card.setStyleSheet("")

    def _action_item(self, action):
        label = self.ACTION_LABELS.get(action, action)
        color = self.ACTION_COLORS.get(action, "#a5b4fc")
        it = QTableWidgetItem(f"● {label}")
        it.setForeground(QColor(color))
        f = it.font(); f.setBold(True); it.setFont(f)
        it.setTextAlignment(Qt.AlignCenter)
        return it

    # ---------- داده ----------
    def _handle_filter_changed(self):
        self._current_page = 1
        self.load_logs()

    def load_logs(self):
        TableSpinner.show(self.table)
        try:
            response = api_client.list_activity_logs(
                page=self._current_page,
                entity_type=self.entity_filter_combo.currentData() or None,
                days=self.days_filter_combo.currentData(),
                user_id=self.user_filter_combo.currentData(),
            )
        except ApiError as e:
            TableSpinner.hide(self.table)
            handle_api_error(self, e, "خطا")
            return
        TableSpinner.hide(self.table)

        self._logs = response["items"]
        self._total_pages = response["total_pages"]

        # کارت‌ها: مجموع واقعی سرور + شمارش عملیاتِ همین صفحه
        from collections import Counter
        counts = Counter(l["action"] for l in self._logs)
        for key, card in self._stat_cards.items():
            card.value_label.setText(
                str(response["total"]) if key is None else str(counts.get(key, 0)))

        self._render()

    def _render(self):
        rows = [l for l in self._logs
                if not self._action_filter or l["action"] == self._action_filter]
        half = math.ceil(len(rows) / 2)
        right, left = rows[:half], rows[half:]
        pairs = max(len(right), len(left))
        self.table.setRowCount(pairs)
        for r, log in enumerate(right):
            self.table.setItem(r, 0, self._action_item(log["action"]))
            self.table.setItem(r, 1, QTableWidgetItem(log.get("user_full_name") or log.get("username") or ""))
            self.table.setItem(r, 2, QTableWidgetItem((log["created_at"] or "")[:16].replace("T", " ")))
        for i, log in enumerate(left):
            r = i
            self.table.setItem(r, 3, QTableWidgetItem((log["created_at"] or "")[:16].replace("T", " ")))
            self.table.setItem(r, 4, QTableWidgetItem(log.get("user_full_name") or log.get("username") or ""))
            self.table.setItem(r, 5, self._action_item(log["action"]))
        self.status_label.setText(
            f"صفحه {self._current_page} از {self._total_pages}"
            + (f" — فیلتر: {self.ACTION_LABELS.get(self._action_filter)}" if self._action_filter else ""))

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

        # --- دکمهٔ تم روشن/تاریک ---
        self._theme_btn = QPushButton("☀️ روشن" if settings_manager.get_theme() == "dark" else "🌙 تاریک")
        self._theme_btn.setObjectName("chip")
        self._theme_btn.setCursor(Qt.PointingHandCursor)
        self._theme_btn.clicked.connect(self._toggle_theme)

        # --- دکمهٔ تنظیمات (تم + اندازه فونت در یک پنجره) ---
        self._settings_btn = QPushButton("⚙️ تنظیمات")
        self._settings_btn.setObjectName("chip")
        self._settings_btn.setCursor(Qt.PointingHandCursor)
        self._settings_btn.clicked.connect(self._open_settings)

        # --- سایدبار + صفحه‌ها ---
        self._sidebar = QListWidget()
        self._sidebar.setObjectName("sideNav")
        # عرض سایدبار با اندازه فونت مقیاس می‌شود تا در فونت بزرگ، متن‌ها بیرون نزنند
        _fs = settings_manager.get_font_size()
        self._sidebar.setFixedWidth(max(210, int(210 * _fs / 13)))
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
            ("💬  گفت‌وگو", ChatTab(), "chat"),
        ]
        if api_client.role == "admin":
            pages += [
                ("👥  مشاوران و مدیریت", None, "agents"),      # lazy
                ("💰  حسابداری پورسانت", None, "deals"),       # lazy
                ("🕘  تاریخچه‌ی فعالیت‌ها", None, "activity"),  # lazy
            ]
        else:
            pages.append(("💰  حساب من", None, "myledger"))     # lazy

        self._lazy_makers = {
            "agents": lambda: AgentCenterTab(),
            "deals": lambda: DealsTab(),
            "activity": lambda: ActivityLogTab(),
            "myledger": lambda: MyLedgerTab(),
        }

        for label, widget, key in pages:
            if widget is None:
                # جای‌نگهدار سبک — واقعی با اولین باز شدن ساخته می‌شود
                widget = QWidget()
            self._stack.addWidget(widget)
            self._sidebar.addItem(label)
            self._index[key] = self._sidebar.count() - 1
            self._page_keys = getattr(self, "_page_keys", {})
            self._page_keys[self._stack.count() - 1] = key

        self._sidebar.currentRowChanged.connect(self._on_sidebar_change)
        self._sidebar.setCurrentRow(self._index["dashboard"])
        self._renewals_tab_index = self._index["renewals"]  # سازگاری با main.py

        side_lay = QVBoxLayout()
        side_lay.setContentsMargins(0, 8, 0, 8)
        side_lay.addWidget(side_title)
        side_lay.addWidget(self._bell_btn)
        side_lay.addWidget(self._theme_btn)
        side_lay.addWidget(self._settings_btn)
        side_lay.addWidget(self._sidebar, 1)


        foot = QFrame()
        foot.setObjectName("sideFooter")
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(10, 8, 10, 8)
        _pal = ["#f5a623", "#7dd3fc", "#86efac", "#c4b5fd"]
        _col = _pal[(len(api_client.full_name or "x")) % 4]
        av = QLabel((api_client.full_name or "?")[:1].upper())
        av.setFixedSize(32, 32); av.setAlignment(Qt.AlignCenter)
        av.setStyleSheet(f"background: {_col}; color: #241300; border-radius: 16px; font-weight: bold;")
        fl.addWidget(av)
        nm = QLabel(f"{api_client.full_name}\n{'مدیر سیستم' if api_client.role == 'admin' else 'مشاور'}")
        nm.setStyleSheet("color: #eceaf4; font-size: 11px; background: transparent;")
        fl.addWidget(nm, 1)
        side_lay.addWidget(foot)

        
        central = QWidget()
        lay = QHBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addLayout(side_lay)
        lay.addWidget(self._stack, 1)
        self.setCentralWidget(central)
        sc = QShortcut(QKeySequence("Ctrl+K"), self)
        sc.activated.connect(self._open_global_search)

        self._notif_timer = QTimer(self)
        self._notif_timer.timeout.connect(self._refresh_bell)
        self._notif_timer.start(60_000)
        QTimer.singleShot(800, self._refresh_bell)

        # --- دکمهٔ شناور چت‌بات (غیرفعال) ---
        self._bot_fab = QPushButton("🤖")
        self._bot_fab.setObjectName("botFab")
        self._bot_fab.setFixedSize(56, 56)
        self._bot_fab.setCursor(Qt.PointingHandCursor)
        self._bot_fab.setToolTip("کاتدر فروش هل — سؤال بپرس")

    def _on_sidebar_change(self, row):
        key = self._page_keys.get(row)
        w = self._stack.widget(row)
        # اگر جای‌نگهدار خالی است، تب واقعی را بساز و جایگزین کن
        if key in self._lazy_makers and w is not None and w.metaObject().className() == "QWidget":
            real = self._lazy_makers[key]()
            old = self._stack.widget(row)
            self._stack.removeWidget(old)
            old.deleteLater()
            self._stack.insertWidget(row, real)
        self._stack.setCurrentIndex(row)


    def _open_global_search(self):
        GlobalSearchDialog(self).exec()

    def switch_to_renewals_tab(self):
        self._sidebar.setCurrentRow(self._index["renewals"])

    # def resizeEvent(self, event):
    #     super().resizeEvent(event)
    #     if hasattr(self, "_bot_fab"):
    #         self._bot_fab.move(20, self.height() - 90)

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

    def _open_settings(self):
        from ui.settings_dialog import SettingsDialog
        SettingsDialog(self).exec()
        # اگر تم یا فونت در دیالوگ عوض شد، اینجا همگام شود
        self._theme_btn.setText("☀️ روشن" if settings_manager.get_theme() == "dark" else "🌙 تاریک")
        self._sidebar.setFixedWidth(max(210, int(210 * settings_manager.get_font_size() / 13)))


    def _toggle_theme(self):
        new_mode = "light" if settings_manager.get_theme() == "dark" else "dark"
        settings_manager.set_theme(new_mode)
        apply_persian_rtl_style(QApplication.instance(), mode=new_mode)
        self._theme_btn.setText("☀️ روشن" if new_mode == "dark" else "🌙 تاریک")

        # رفرش حباب‌های چت با تم جدید (هم گفت‌وگوی انسانی، هم صفحه‌ی ربات)
        try:
            for i in range(self._stack.count()):
                wd = self._stack.widget(i)
                if isinstance(wd, ChatTab):
                    if wd.current_peer is not None:
                        wd.load_conversation()
                    else:
                        wd._load_bot_greeting()
        except Exception:
            pass