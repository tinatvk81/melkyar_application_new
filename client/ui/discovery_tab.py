import webbrowser
import re as _re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QAbstractItemView, QDialog, QFormLayout,
    QComboBox, QCheckBox, QListWidget, QListWidgetItem, QMessageBox, QTextEdit,
)
from PySide6.QtGui import QColor

from api_client import api_client, ApiError
from session import handle_api_error
from ui.spinner import TableSpinner
from ui.toast import Toast
from ui.property_form import PropertyFormDialog

DEAL_TYPE_FA = {"sale": "فروش", "rent": "اجاره", "mortgage": "رهن کامل", "presale": "پیش‌خرید"}

TABLE_QSS = (
    "QTableWidget { border: none; font-size: 14px; }"
    "QTableWidget::item { padding: 8px; border-bottom: 1px solid rgba(128,128,140,0.30); }"
    "QTableWidget::item:selected { background: rgba(245,166,35,0.28); }"
    "QHeaderView::section { font-size: 13px; padding: 8px; }"
)

PHONE_WARN = ("شمارهٔ تماس مالک در ملک‌یاب ذخیره نمی‌شود (دیوار آن را پشت «اطلاعات تماس» مخفی می‌کند).\n\n"
              "ترتیب پیشنهادی:\n"
              "۱) «باز کردن در دیوار» را بزن\n۲) «اطلاعات تماس» → شماره را بردار\n"
              "۳) برگرد و «افزودن با فرم» بزن و شماره را در «تلفن مالک» بنویس\n\n"
              "اگر بدون شماره اضافه کنی، بعداً باید از «فهرست فایل‌ها» پیدایش کنی و تکمیلش کنی.")


def _warn_phone(parent) -> bool:
    """True = کاربر فهمید و ادامه می‌دهد."""
    box = QMessageBox(parent)
    box.setWindowTitle("یادآوری: شمارهٔ تماس")
    box.setIcon(QMessageBox.Warning)
    box.setText(PHONE_WARN)
    box.addButton("متوجه شدم — ادامه", QMessageBox.AcceptRole)
    box.addButton("انصراف", QMessageBox.RejectRole)
    box.exec()
    return box.clickedButton() is box.buttons()[0]


class SubscriptionDialog(QDialog):
    def __init__(self, neighborhoods):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("تنظیمات مناطق من — ملک‌یاب")
        self.resize(760, 600)
        try:
            cur = api_client.get_discovery_subscription()
        except ApiError:
            cur = {"allowed_districts": [], "blocked_districts": [], "deal_types": [], "show_unknown": True}

        lay = QVBoxLayout(self)
        tip = QLabel("⚠️ اگر «فقط این محله‌ها» پر باشد، بلک‌لیست بی‌اثر است. خالی = همهٔ محله‌ها.\n"
                     "محله‌های بلک‌لیست حتی در لیست هم نمی‌آیند (فیلتر سمت سرور).")
        tip.setStyleSheet("color:#f5a623; background:transparent; font-size:13px;")
        lay.addWidget(tip)

        cols = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("✅ فقط این محله‌ها (خالی = همه):"))
        self.allowed_list = QListWidget()
        for n in neighborhoods:
            it = QListWidgetItem(n["name"])
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if n["name"] in (cur.get("allowed_districts") or []) else Qt.Unchecked)
            self.allowed_list.addItem(it)
        left.addWidget(self.allowed_list)
        lw = QWidget(); lw.setLayout(left)

        right = QVBoxLayout()
        right.addWidget(QLabel("🚫 هرگز این محله‌ها را نشان نده:"))
        self.blocked_list = QListWidget()
        for n in neighborhoods:
            it = QListWidgetItem(n["name"])
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if n["name"] in (cur.get("blocked_districts") or []) else Qt.Unchecked)
            self.blocked_list.addItem(it)
        right.addWidget(self.blocked_list)
        rw = QWidget(); rw.setLayout(right)

        cols.addWidget(lw); cols.addWidget(rw)
        lay.addLayout(cols, 1)

        dt_row = QHBoxLayout()
        dt_row.addWidget(QLabel("نوع معامله (خالی = همه):"))
        self.deal_checks = {}
        for key, label in [("sale", "فروش"), ("rent", "اجاره"), ("mortgage", "رهن کامل")]:
            cb = QCheckBox(label)
            cb.setChecked(key in (cur.get("deal_types") or []))
            self.deal_checks[key] = cb
            dt_row.addWidget(cb)
        dt_row.addStretch()
        lay.addLayout(dt_row)

        self.unknown_check = QCheckBox("آگهی‌های بدون محله هم نمایش داده شود")
        self.unknown_check.setChecked(bool(cur.get("show_unknown", True)))
        lay.addWidget(self.unknown_check)

        save = QPushButton("ذخیره"); save.setObjectName("primary")
        save.clicked.connect(self._save)
        lay.addWidget(save)

    def _collect(self, lw):
        return [lw.item(i).text() for i in range(lw.count()) if lw.item(i).checkState() == Qt.Checked]

    def _save(self):
        payload = {
            "allowed_districts": self._collect(self.allowed_list),
            "blocked_districts": self._collect(self.blocked_list),
            "deal_types": [k for k, cb in self.deal_checks.items() if cb.isChecked()],
            "show_unknown": self.unknown_check.isChecked(),
        }
        try:
            api_client.update_discovery_subscription(payload)
        except ApiError as e:
            handle_api_error(self, e, "خطا در ذخیره تنظیمات")
            return
        Toast.show("✅ تنظیمات مناطق ذخیره شد")
        self.accept()


class AssignDialog(QDialog):
    def __init__(self, neighborhoods):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("تعیین محله برای این آگهی")
        form = QFormLayout()
        self.combo = QComboBox()
        for n in neighborhoods:
            self.combo.addItem(n["name"], n["id"])
        form.addRow("محله:", self.combo)
        ok = QPushButton("ثبت"); ok.setObjectName("primary"); ok.clicked.connect(self.accept)
        lay = QVBoxLayout(self); lay.addLayout(form); lay.addWidget(ok)

    def selected_id(self):
        return self.combo.currentData()


class ListingDetailDialog(QDialog):
    def __init__(self, item, on_add, on_dismiss):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.item = item
        self.on_add = on_add
        self.on_dismiss = on_dismiss
        self.setWindowTitle("جزئیات آگهی — ملک‌یاب")
        self.resize(880, 700)

        attrs = item.get("attributes") or {}
        lay = QVBoxLayout(self)

        t = QLabel(item.get("title") or "—")
        t.setWordWrap(True)
        t.setStyleSheet("font-size:17px; font-weight:800; color:#f5a623; background:transparent;")
        lay.addWidget(t)

        src = "دیوار" if item.get("source") == "divar" else (item.get("source") or "—")
        dt = item.get("deal_type")
        info = QLabel(f"منبع: {src}   |   نوع: {DEAL_TYPE_FA.get(dt, dt or '—')}   |   "
                      f"شهر: {item.get('city') or '—'}   |   محله: {item.get('raw_address') or '—'}   |   "
                      f"تاریخ: {(item.get('posted_at') or '')[:16].replace('T', ' ')}")
        info.setWordWrap(True)
        info.setStyleSheet("color: rgba(236,234,244,0.85); background:transparent;")
        lay.addWidget(info)

        form = QFormLayout()
        area, rooms = item.get("area_m2"), item.get("rooms")
        extra = []
        if attrs.get("build_year"):
            extra.append(f"ساخت {attrs['build_year']}")
        if attrs.get("floor"):
            extra.append(f"طبقه {attrs['floor']}")
        form.addRow("متراژ / اتاق:", QLabel(
            (f"{area} متر / {rooms} اتاق" if (area or rooms) else "—")
            + ((" — " + "، ".join(extra)) if extra else "")))

        price, dep, rent = item.get("price"), item.get("deposit"), item.get("monthly_rent")
        if price:
            m = QLabel(f"{price:,} تومان"); m.setStyleSheet("font-weight:800; color:#f5a623; font-size:15px;")
            form.addRow("قیمت کل:", m)
        elif dep and rent:
            m = QLabel(f"ودیعه {dep:,} — اجارهٔ ماهانه {rent:,} تومان")
            m.setStyleSheet("font-weight:800; color:#f5a623; font-size:15px;")
            form.addRow("اجاره:", m)
        elif dep:
            m = QLabel(f"{dep:,} تومان"); m.setStyleSheet("font-weight:800; color:#f5a623; font-size:15px;")
            form.addRow("رهن کامل:", m)
        else:
            form.addRow("قیمت:", QLabel("—"))
        if attrs.get("advertiser"):
            form.addRow("آگهی‌دهنده:", QLabel(attrs["advertiser"]))
        lay.addLayout(form)

        if attrs.get("amenities"):
            am = QLabel("✅ " + "، ".join(attrs["amenities"]))
            am.setWordWrap(True)
            am.setStyleSheet("color:#86efac; background:transparent; font-size:13px;")
            lay.addWidget(QLabel("ویژگی‌ها و امکانات:"))
            lay.addWidget(am)

        lay.addWidget(QLabel("توضیحات آگهی:"))
        desc_box = QTextEdit(attrs.get("description") or "—")
        desc_box.setReadOnly(True)
        desc_box.setMinimumHeight(180)
        _html = _re.sub(r"(https?://[^\s]+)", r'<a href="\1">\1</a>', (attrs.get("description") or "—").replace("\n", "<br>"))
        desc_box.setHtml(_html)
        desc_box.setOpenExternalLinks(True)
        desc_box.setTextInteractionFlags(Qt.TextBrowserInteraction)

        lay.addWidget(desc_box, 1)

        note = QLabel("شمارهٔ تماس در خود دیوار است — دکمهٔ زیر → «اطلاعات تماس».")
        note.setStyleSheet("color: rgba(128,128,140,1); font-size:11px; background:transparent;")
        lay.addWidget(note)

        open_btn = QPushButton("🔗 باز کردن در دیوار (شمارهٔ تماس)")
        open_btn.setObjectName("chip")
        open_btn.clicked.connect(lambda: webbrowser.open(item.get("url") or "https://divar.ir"))
        add_btn = QPushButton("➕ افزودن با فرم")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add)
        dismiss_btn = QPushButton("🚫 نادیده بگیر")
        dismiss_btn.setObjectName("chip")
        dismiss_btn.clicked.connect(self._dismiss)
        btns = QHBoxLayout()
        btns.addWidget(dismiss_btn); btns.addStretch()
        btns.addWidget(open_btn); btns.addWidget(add_btn)
        lay.addLayout(btns)

    def _add(self):
        box = QMessageBox(self)
        box.setWindowTitle("یادآوری: شمارهٔ تماس")
        box.setIcon(QMessageBox.Warning)
        box.setText(PHONE_WARN)
        b_open = box.addButton("🔗 باز کردن دیوار برای گرفتن شماره", QMessageBox.AcceptRole)
        b_go = box.addButton("➕ همان‌جا ادامهٔ افزودن", QMessageBox.ActionRole)
        box.addButton("انصراف", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is b_open:
            import webbrowser
            webbrowser.open(self.item.get("url") or "https://divar.ir")
            Toast.show("شماره را برداشت؟ برگرد و «افزودن با فرم» را بزن — فرم باز است")
            return
        if box.clickedButton() is b_go:
            import webbrowser
            webbrowser.open(self.item.get("url") or "https://divar.ir")
            self.accept()
            self.on_add(self.item)


    def _dismiss(self):
        self.accept(); self.on_dismiss(self.item)


class DiscoveryTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._listings = []
        self._row_map = []
        self._neighborhoods = []
        try:
            self._neighborhoods = api_client.get_discovery_neighborhoods()
        except ApiError:
            pass

        title = QLabel("📡 یافته‌های ملک‌یاب")
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #f5a623; background: transparent;")
        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: rgba(128,128,140,1); background: transparent;")

        self.unknown_chip = QPushButton("🧭 بدون محله")
        self.unknown_chip.setObjectName("chip")
        self.unknown_chip.setCheckable(True)
        self.unknown_chip.setCursor(Qt.PointingHandCursor)
        self.unknown_chip.setToolTip("فقط آگهی‌هایی که محله‌شان تشخیص داده نشده — برای دسته‌بندی دستی")
        self.unknown_chip.toggled.connect(self._toggle_unknown)

        self.source_combo = QComboBox()
        for v, l in [("", "همهٔ منابع"), ("divar", "دیوار"), ("sheypoor", "شیپور")]:
            self.source_combo.addItem(l, v)
        self.deal_combo = QComboBox()
        for v, l in [("", "همهٔ انواع"), ("sale", "فروش"), ("rent", "اجاره"), ("mortgage", "رهن کامل")]:
            self.deal_combo.addItem(l, v)
        self.district_combo = QComboBox()
        self._fill_district_combo()
        for c in (self.source_combo, self.deal_combo, self.district_combo):
            c.currentIndexChanged.connect(self._render)

        settings_btn = QPushButton("⚙️ مناطق من")
        settings_btn.setObjectName("chip")
        settings_btn.setToolTip("وایت‌لیست/بلک‌لیست محله‌ها + نوع معامله — مخصوص خودت")
        settings_btn.clicked.connect(self._open_subscription)
        refresh_btn = QPushButton("🔄 به‌روزرسانی")
        refresh_btn.setObjectName("chip")
        refresh_btn.clicked.connect(self.refresh)

        filter_row = QHBoxLayout()
        filter_row.addWidget(self.unknown_chip)
        filter_row.addWidget(QLabel("منبع:")); filter_row.addWidget(self.source_combo)
        filter_row.addWidget(QLabel("نوع:")); filter_row.addWidget(self.deal_combo)
        filter_row.addWidget(QLabel("محله:")); filter_row.addWidget(self.district_combo)
        filter_row.addStretch()
        filter_row.addWidget(settings_btn)
        filter_row.addWidget(refresh_btn)

        head = QHBoxLayout()
        head.addWidget(title); head.addSpacing(12); head.addWidget(self.count_label); head.addStretch()

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["✓", "عنوان", "محله", "قیمت", "نوع", "منبع", "تاریخ", "اقدام‌ها"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.setStyleSheet(TABLE_QSS)
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.doubleClicked.connect(lambda _: self._open_detail())

        self.select_all_btn = QPushButton("☑ انتخاب همه/هیچ")
        self.select_all_btn.setObjectName("chip")
        self.select_all_btn.setToolTip("تیک زدن/برداشتن همهٔ ردیف‌های نمایش‌داده‌شده")
        self.select_all_btn.clicked.connect(self._toggle_select_all)
        self.fast_btn = QPushButton("⚡ افزودن سریع انتخاب‌شده‌ها")
        self.fast_btn.setObjectName("primary")
        self.fast_btn.setToolTip("بدون فرم — فایل با دادهٔ آگهی ساخته می‌شود؛ بعداً از «فهرست فایل‌ها» ویرایشش کن")
        self.fast_btn.clicked.connect(self._bulk_add)
        self.form_btn = QPushButton("📝 افزودن با فرم (ردیف انتخابی)")
        self.form_btn.setToolTip("یک ردیف را انتخاب کن → جزئیات کامل → فرم از پیش پرشده")
        self.form_btn.clicked.connect(self._open_detail)
        self.dismiss_btn = QPushButton("🚫 نادیده گرفتن انتخاب‌شده‌ها")
        self.dismiss_btn.setObjectName("chip")
        self.dismiss_btn.setToolTip("آگهی‌های تیک‌خورده از لیست حذف می‌شوند")
        self.dismiss_btn.clicked.connect(self._dismiss_checked)
        actions = QHBoxLayout()
        actions.addWidget(self.select_all_btn)
        actions.addWidget(self.fast_btn); actions.addWidget(self.form_btn); actions.addWidget(self.dismiss_btn)
        actions.addStretch()
        self.sel_label = QLabel("")
        actions.addWidget(self.sel_label)

        hint = QLabel("تیک = انتخاب برای عمل گروهی | دابل‌کلیک ردیف = جزئیات کامل | "
                      "دکمه‌های ستون «اقدام‌ها»: ⚡ افزودن سریع همین یکی، 🚫 نادیده، 🧭 تعیین محله")
        hint.setStyleSheet("color: rgba(128,128,140,1); background: transparent;")

        lay = QVBoxLayout(self)
        lay.addLayout(head)
        lay.addLayout(filter_row)
        lay.addWidget(self.table, 1)
        lay.addLayout(actions)
        lay.addWidget(hint)
        self.refresh()

    def _fill_district_combo(self):
        self.district_combo.blockSignals(True)
        self.district_combo.clear()
        self.district_combo.addItem("همه", "")
        self.district_combo.addItem("🧭 بدون محله", "unknown")
        for n in self._neighborhoods:
            self.district_combo.addItem(n["name"], n["id"])
        self.district_combo.blockSignals(False)

    def _open_subscription(self):
        if not self._neighborhoods:
            try:
                self._neighborhoods = api_client.get_discovery_neighborhoods()
            except ApiError:
                self._neighborhoods = []
        if not self._neighborhoods:
            QMessageBox.warning(self, "خطا", "لیست محله‌ها خالی است.")
            return
        if SubscriptionDialog(self._neighborhoods).exec() == QDialog.Accepted:
            self.refresh()

    def refresh(self):
        TableSpinner.show(self.table)
        try:
            self._listings = api_client.list_discovered_listings(only_new=True)
        except ApiError as e:
            TableSpinner.hide(self.table)
            handle_api_error(self, e, "خطا در دریافت یافته‌ها")
            return
        TableSpinner.hide(self.table)
        self._render()

    def _visible_rows(self):
        src = self.source_combo.currentData() or ""
        dt = self.deal_combo.currentData() or ""
        dist = self.district_combo.currentData() or ""
        out = []
        for it in self._listings:
            if src and it.get("source") != src:
                continue
            if dt and it.get("deal_type") != dt:
                continue
            if dist == "unknown" and it.get("neighborhood_id") is not None:
                continue
            if dist and dist != "unknown" and it.get("neighborhood_id") != dist:
                continue
            out.append(it)
        return out

    def _price_text(self, it):
        if it.get("price"):
            return f"{it['price']:,}"
        if it.get("deposit") and it.get("monthly_rent"):
            return f"ودیعه {it['deposit']:,} / اجاره {it['monthly_rent']:,}"
        if it.get("deposit"):
            return f"رهن {it['deposit']:,}"
        return "—"

    def _render(self):
        rows = self._visible_rows()
        unknown_n = sum(1 for it in self._listings if it.get("neighborhood_id") is None)
        self.unknown_chip.setText(f"🧭 بدون محله ({unknown_n})")
        self.count_label.setText(f"{len(rows)} یافته از {len(self._listings)}")
        self.table.setRowCount(len(rows))
        self._row_map = rows
        for row, it in enumerate(rows):
            chk = QTableWidgetItem()
            chk.setFlags(chk.flags() | Qt.ItemIsUserCheckable)
            chk.setCheckState(Qt.Unchecked)
            self.table.setItem(row, 0, chk)
            self.table.setItem(row, 1, QTableWidgetItem(it.get("title") or ""))
            self.table.setItem(row, 2, QTableWidgetItem(it.get("raw_address") or "—"))
            p = QTableWidgetItem(self._price_text(it))
            p.setForeground(QColor("#f5a623"))
            f = p.font(); f.setBold(True); p.setFont(f)
            self.table.setItem(row, 3, p)
            dtv = it.get("deal_type")
            self.table.setItem(row, 4, QTableWidgetItem(DEAL_TYPE_FA.get(dtv, dtv or "—")))
            self.table.setItem(row, 5, QTableWidgetItem("دیوار" if it.get("source") == "divar" else (it.get("source") or "")))
            self.table.setItem(row, 6, QTableWidgetItem((it.get("posted_at") or "")[:10]))

            acts = QWidget()
            ah = QHBoxLayout(acts); ah.setContentsMargins(2, 2, 2, 2); ah.setSpacing(4)
            ab = QPushButton("⚡ افزودن")
            ab.setObjectName("chip")
            ab.setToolTip("افزودن سریع همین آگهی به فایل‌ها (بدون فرم)")
            ab.clicked.connect(lambda _=False, x=it: self._quick_add_one(x))
            ah.addWidget(ab)
            bx = QPushButton("🚫 نادیده")
            bx.setObjectName("chip")
            bx.setToolTip("این آگهی از لیست حذف می‌شود")
            bx.clicked.connect(lambda _=False, x=it: self._dismiss_one(x))
            ah.addWidget(bx)
            if it.get("neighborhood_id") is None:
                nb = QPushButton("🧭 محله")
                nb.setObjectName("chip")
                nb.setToolTip("محلهٔ این آگهی را دستی تعیین کن")
                nb.clicked.connect(lambda _=False, x=it: self._assign(x))
                ah.addWidget(nb)
            acts.setLayout(ah)
            self.table.setCellWidget(row, 7, acts)

        if not rows:
            self.table.setRowCount(1)
            e = QTableWidgetItem("یافته‌ای با این فیلترها نیست")
            e.setForeground(QColor("#86efac"))
            self.table.setItem(0, 0, e)
            self.table.setSpan(0, 0, 1, 8)
        self._update_sel_label()

    def _toggle_unknown(self, checked):
        self.district_combo.blockSignals(True)
        self.district_combo.setCurrentIndex(1 if checked else 0)
        self.district_combo.blockSignals(False)
        self._render()

    def _toggle_select_all(self):
        rows = self._visible_rows()
        if not rows:
            return
        any_unchecked = any(
            (c := self.table.item(r, 0)) and c.checkState() != Qt.Checked
            for r in range(len(rows))
        )
        state = Qt.Checked if any_unchecked else Qt.Unchecked
        for r in range(len(rows)):
            self.table.item(r, 0).setCheckState(state)
        self._update_sel_label()

    def _assign(self, it):
        if not self._neighborhoods:
            QMessageBox.warning(self, "خطا", "لیست محله‌ها خالی است.")
            return
        dlg = AssignDialog(self._neighborhoods)
        if dlg.exec() != QDialog.Accepted:
            return
        try:
            api_client.assign_discovery_neighborhood(it["id"], dlg.selected_id())
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        Toast.show("محله ثبت شد")
        self.refresh()

    def _checked_ids(self):
        return [it["id"] for row, it in enumerate(self._row_map)
                if (c := self.table.item(row, 0)) and c.checkState() == Qt.Checked]

    def _update_sel_label(self):
        n = len(self._checked_ids())
        self.sel_label.setText(f"{n} مورد انتخاب شده" if n else "")

    def _on_cell_clicked(self, row, col):
        if col == 0:
            self._update_sel_label()

    def _bulk_add(self):
        ids = self._checked_ids()
        if not ids:
            QMessageBox.information(self, "توجه", "اول با تیک، آگهی‌ها را انتخاب کن.")
            return
        if not _warn_phone(self):
            return
        created_total, failed_total = 0, 0
        for i in range(0, len(ids), 50):
            try:
                res = api_client.bulk_add_discovered(ids[i:i + 50])
            except ApiError as e:
                handle_api_error(self, e, "خطا در افزودن گروهی")
                return
            created_total += len(res.get("created") or [])
            failed_total += len(res.get("failed") or [])
        Toast.show(f"⚡ {created_total} فایل ساخته شد" + (f" — {failed_total} ناموفق" if failed_total else ""))
        self.refresh()

    def _quick_add_one(self, it):
        if not _warn_phone(self):
            return
        try:
            res = api_client.bulk_add_discovered([it["id"]])
        except ApiError as e:
            handle_api_error(self, e, "خطا")
            return
        if res.get("created"):
            prop = (res["created"][0] or {}).get("property")
            self.refresh()
            if prop:
                Toast.show(f"⚡ فایل #{prop['id']} ساخته شد — شمارهٔ تماس را همین‌جا بگذار")
                PropertyFormDialog(property_data=prop, on_saved=self.refresh).exec()
            else:
                Toast.show("⚡ فایل ساخته شد")
        else:
            Toast.show("این آگهی قبلاً اضافه شده بود")

            
    def _open_detail(self):
        row = self.table.currentRow()
        if not (0 <= row < len(self._row_map)):
            QMessageBox.information(self, "توجه", "اول یک ردیف را انتخاب کن (یا دابل‌کلیک کن).")
            return
        it = self._row_map[row]
        attrs = it.get("attributes") or {}
        if not attrs.get("description"):
            try:
                it = api_client.refresh_discovery_details(it["id"])
                for i, x in enumerate(self._listings):
                    if x["id"] == it["id"]:
                        self._listings[i] = it
            except ApiError:
                pass
        ListingDetailDialog(it, on_add=self._add_with_form, on_dismiss=self._dismiss_one).exec()

    @staticmethod
    def _prefill_from(it: dict) -> dict:
        attrs = it.get("attributes") or {}
        note_lines = [f"وارد شده از ملک‌یاب — منبع: {it.get('source')}", it.get("title") or ""]
        desc = (attrs.get("description") or "").strip()
        if desc:
            note_lines.append("— توضیحات آگهی —")
            note_lines.append(desc)   # کامل — بدون محدودیت
        return {
            "deal_type": it.get("deal_type") or "sale",
            "city": it.get("city"),
            "district": it.get("raw_address"),
            "area_m2": it.get("area_m2"),
            "rooms": it.get("rooms"),
            "price": it.get("price"),
            "deposit": it.get("deposit"),
            "monthly_rent": it.get("monthly_rent"),
            "build_year": attrs.get("build_year"),
            "amenities": attrs.get("amenities") or [],
            "source_note": "\n".join(x for x in note_lines if x),
            "updated_fa": next((t for t in (attrs.get("timestamps") or []) if "به\u200cروزرسانی" in t or "به روزرسانی" in t), ""),
            "address_full": it.get("raw_address"),
            "url": it.get("url"),
            "listing_id": it.get("id"),
        }

    def _add_with_form(self, it: dict):
        PropertyFormDialog(property_data=None, on_saved=self.refresh,
                           prefill=self._prefill_from(it)).exec()

    def _dismiss_one(self, it):
        self._dismiss_ids([it["id"]])

    def _dismiss_checked(self):
        ids = self._checked_ids()
        if not ids:
            QMessageBox.information(self, "توجه", "اول با تیک انتخاب کن.")
            return
        self._dismiss_ids(ids)

    def _dismiss_ids(self, ids):
        for lid in ids:
            try:
                api_client.dismiss_discovery_listing(lid)
            except ApiError as e:
                handle_api_error(self, e, "خطا")
                return
        Toast.show(f"{len(ids)} آگهی نادیده گرفته شد")
        self.refresh()