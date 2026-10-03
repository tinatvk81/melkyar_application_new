import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QAbstractItemView, QDialog, QFormLayout,
    QComboBox, QCheckBox, QListWidget, QListWidgetItem, QFrame,
)
from PySide6.QtGui import QColor

from api_client import api_client, ApiError
from session import handle_api_error
from ui.spinner import TableSpinner
from ui.toast import Toast
from ui.property_form import PropertyFormDialog

DEAL_TYPE_FA = {"sale": "فروش", "rent": "اجاره", "mortgage": "رهن کامل", "presale": "پیش‌خرید"}


class SubscriptionDialog(QDialog):
    """تنظیمات مناطق من — وایت‌لیست/بلک‌لیست محله‌ها + نوع معامله + نامعلول‌ها."""

    def __init__(self, neighborhoods: list[dict]):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("تنظیمات مناطق من — ملک‌یاب")
        self.resize(720, 560)
        try:
            cur = api_client.get_discovery_subscription()
        except ApiError:
            cur = {"allowed_districts": [], "blocked_districts": [], "deal_types": [], "show_unknown": True}

        lay = QVBoxLayout(self)
        tip = QLabel("⚠️ اگر «فقط این محله‌ها» پر باشد، بلک‌لیست بی‌اثر است. خالی = همهٔ محله‌ها.")
        tip.setStyleSheet("color:#f5a623; background:transparent;")
        lay.addWidget(tip)

        cols = QHBoxLayout()
        # وایت‌لیست
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
        # بلک‌لیست
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

    def _collect(self, lw: QListWidget) -> list[str]:
        out = []
        for i in range(lw.count()):
            it = lw.item(i)
            if it.checkState() == Qt.Checked:
                out.append(it.text())
        return out

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
    """تعیین محله برای آگهی‌های بدون محله."""

    def __init__(self, neighborhoods: list[dict]):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("تعیین محله")
        self.neighborhoods = neighborhoods
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
        self.setWindowTitle("جزئیات آگهی — ملک‌یاب")
        self.resize(560, 560)

        attrs = item.get("attributes") or {}
        form = QFormLayout()
        form.addRow("عنوان:", QLabel(item.get("title") or "—"))
        src = "دیوار" if item.get("source") == "divar" else (item.get("source") or "—")
        form.addRow("منبع:", QLabel(src))
        dt = item.get("deal_type")
        form.addRow("نوع:", QLabel(DEAL_TYPE_FA.get(dt, dt or "—")))
        form.addRow("شهر/محله:", QLabel(f"{item.get('city') or '—'} — {item.get('raw_address') or '—'}"))
        area, rooms = item.get("area_m2"), item.get("rooms")
        extra = []
        if attrs.get("build_year"):
            extra.append(f"ساخت {attrs['build_year']}")
        if attrs.get("floor"):
            extra.append(f"طبقه {attrs['floor']}")
        form.addRow("متراژ/اتاق:", QLabel(
            (f"{area} متر / {rooms} اتاق" if (area or rooms) else "—")
            + ((" — " + "، ".join(extra)) if extra else "")))

        price, dep, rent = item.get("price"), item.get("deposit"), item.get("monthly_rent")
        if price:
            m = QLabel(f"{price:,} تومان"); m.setStyleSheet("font-weight:800; color:#f5a623;")
            form.addRow("قیمت کل:", m)
        elif dep and rent:
            m = QLabel(f"ودیعه {dep:,} — اجاره {rent:,}"); m.setStyleSheet("font-weight:800; color:#f5a623;")
            form.addRow("اجاره:", m)
        elif dep:
            m = QLabel(f"{dep:,} تومان"); m.setStyleSheet("font-weight:800; color:#f5a623;")
            form.addRow("رهن کامل:", m)
        else:
            form.addRow("قیمت:", QLabel("—"))
        form.addRow("تاریخ:", QLabel((item.get("posted_at") or "")[:16].replace("T", " ")))

        if attrs.get("amenities"):
            am = QLabel("✅ " + "، ".join(attrs["amenities"]))
            am.setWordWrap(True)
            form.addRow("امکانات:", am)
        desc = attrs.get("description")
        if desc:
            d = QLabel(desc[:900]); d.setWordWrap(True)
            d.setStyleSheet("background: rgba(255,255,255,0.04); border-radius: 8px; padding: 8px;")
            d.setMaximumHeight(160)
            form.addRow("توضیحات:", d)

        note = QLabel("شمارهٔ تماس در خود دیوار است — با دکمهٔ زیر آگهی را باز کن و «اطلاعات تماس» را بزن.")
        note.setWordWrap(True)
        note.setStyleSheet("color: rgba(128,128,140,1); font-size: 10px;")

        open_btn = QPushButton("🔗 باز کردن در دیوار (شمارهٔ تماس)")
        open_btn.setObjectName("chip")
        open_btn.clicked.connect(lambda: webbrowser.open(item.get("url") or "https://divar.ir"))
        add_btn = QPushButton("➕ افزودن با فرم")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add)
        dismiss_btn = QPushButton("نادیده بگیر")
        dismiss_btn.setObjectName("chip")
        dismiss_btn.clicked.connect(self._dismiss)
        btns = QHBoxLayout()
        btns.addWidget(dismiss_btn); btns.addStretch()
        btns.addWidget(open_btn); btns.addWidget(add_btn)

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(note)
        lay.addLayout(btns)

    def _add(self):
        self.accept(); self.on_add(self.item)

    def _dismiss(self):
        self.accept(); self.on_dismiss(self.item)


class DiscoveryTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self._listings = []
        self._neighborhoods = []
        try:
            self._neighborhoods = api_client.get_discovery_neighborhoods()
        except ApiError:
            pass

        title = QLabel("📡 یافته‌های ملک‌یاب")
        title.setStyleSheet("font-size: 15px; font-weight: 800; color: #f5a623; background: transparent;")
        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: rgba(128,128,140,1); background: transparent;")

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
        settings_btn.clicked.connect(self._open_subscription)
        refresh_btn = QPushButton("🔄 به‌روزرسانی")
        refresh_btn.setObjectName("chip")
        refresh_btn.clicked.connect(self.refresh)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("منبع:")); filter_row.addWidget(self.source_combo)
        filter_row.addWidget(QLabel("نوع:")); filter_row.addWidget(self.deal_combo)
        filter_row.addWidget(QLabel("محله:")); filter_row.addWidget(self.district_combo)
        filter_row.addStretch()
        filter_row.addWidget(settings_btn)
        filter_row.addWidget(refresh_btn)

        head = QHBoxLayout()
        head.addWidget(title); head.addSpacing(12); head.addWidget(self.count_label); head.addStretch()

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["✓", "عنوان", "محله", "قیمت", "نوع", "منبع", "تاریخ"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setStyleSheet(
            "QTableWidget { border: none; }"
            "QTableWidget::item { padding: 6px; border-bottom: 1px solid rgba(128,128,140,0.30); }"
            "QTableWidget::item:selected { background: rgba(245,166,35,0.28); }")
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.doubleClicked.connect(lambda _: self._open_detail())

        self.fast_btn = QPushButton("⚡ افزودن سریع انتخاب‌شده‌ها")
        self.fast_btn.setObjectName("primary")
        self.fast_btn.setToolTip("بدون فرم — فایل با دادهٔ آگهی ساخته می‌شود؛ بعداً از فهرست فایل‌ها ویرایش کن")
        self.fast_btn.clicked.connect(self._bulk_add)
        self.form_btn = QPushButton("📝 افزودن با فرم")
        self.form_btn.clicked.connect(self._open_detail)
        self.dismiss_btn = QPushButton("🚫 نادیده گرفتن")
        self.dismiss_btn.setObjectName("chip")
        self.dismiss_btn.clicked.connect(self._dismiss_checked)
        actions = QHBoxLayout()
        actions.addWidget(self.fast_btn); actions.addWidget(self.form_btn); actions.addWidget(self.dismiss_btn)
        actions.addStretch()
        self.sel_label = QLabel("")
        actions.addWidget(self.sel_label)

        # --- پنل نامعلول‌ها (مثل حسابداری، جدا) ---
        self.unknown_frame = QFrame()
        self.unknown_frame.setObjectName("statCard")
        uf = QVBoxLayout(self.unknown_frame)
        self.unknown_title = QLabel("🧭 آگهی‌های بدون محله — نیاز به دسته‌بندی")
        self.unknown_title.setStyleSheet("font-weight:800; color:#fbbf24; background:transparent;")
        self.unknown_table = QTableWidget()
        self.unknown_table.setColumnCount(4)
        self.unknown_table.setHorizontalHeaderLabels(["عنوان", "قیمت", "منبع", ""])
        self.unknown_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.unknown_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.unknown_table.verticalHeader().setVisible(False)
        self.unknown_table.setMaximumHeight(150)
        uf.addWidget(self.unknown_title); uf.addWidget(self.unknown_table)

        hint = QLabel("تیک بزن → افزودن سریع گروهی | دابل‌کلیک = جزئیات کامل")
        hint.setStyleSheet("color: rgba(128,128,140,1); background: transparent;")

        lay = QVBoxLayout(self)
        lay.addLayout(head)
        lay.addLayout(filter_row)
        lay.addWidget(self.table, 1)
        lay.addLayout(actions)
        lay.addWidget(self.unknown_frame)
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
        if not rows:
            self.table.setRowCount(1)
            e = QTableWidgetItem("یافته‌ای با این فیلترها نیست")
            e.setForeground(QColor("#86efac"))
            self.table.setItem(0, 0, e)
            self.table.setSpan(0, 0, 1, 7)
        self._update_sel_label()
        self._render_unknown()

    def _render_unknown(self):
        unknowns = [it for it in self._listings if it.get("neighborhood_id") is None]
        self.unknown_frame.setVisible(bool(unknowns))
        self.unknown_title.setText(f"🧭 آگهی‌های بدون محله ({len(unknowns)}) — نیاز به دسته‌بندی")
        t = self.unknown_table
        t.setRowCount(len(unknowns))
        for r, it in enumerate(unknowns):
            t.setItem(r, 0, QTableWidgetItem(it.get("title") or ""))
            t.setItem(r, 1, QTableWidgetItem(self._price_text(it)))
            t.setItem(r, 2, QTableWidgetItem("دیوار" if it.get("source") == "divar" else (it.get("source") or "")))
            btn = QPushButton("تعیین محله")
            btn.setObjectName("chip")
            btn.clicked.connect(lambda _=False, x=it: self._assign(x))
            t.setCellWidget(r, 3, btn)

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
        ids = []
        for row, it in enumerate(self._row_map):
            c = self.table.item(row, 0)
            if c and c.checkState() == Qt.Checked:
                ids.append(it["id"])
        return ids

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

    def _open_detail(self):
        row = self.table.currentRow()
        if not (0 <= row < len(self._row_map)):
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
        note_lines = [f"وارد شده از ملک‌یاب — منبع: {it.get('source')}", it.get("title") or "", it.get("url") or ""]
        desc = (attrs.get("description") or "").strip()
        if desc:
            note_lines.append("— توضیحات آگهی —")
            note_lines.append(desc[:600])
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
            "listing_id": it.get("id"),
        }

    def _add_with_form(self, it: dict):
        PropertyFormDialog(property_data=None, on_saved=self.refresh,
                           prefill=self._prefill_from(it)).exec()

    def _dismiss_one(self, it: dict):
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