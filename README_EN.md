

# 🏠 Melkyar — Multi-User Real Estate Listing Management (Cloud Desktop App)

**Melkyar** is a real-estate office management system:
each agent runs a lightweight desktop app that connects over HTTPS to a cloud server.
The admin sees everything; each agent sees only their own listings — and that rule
is enforced **server-side**, not in the client.

**Architecture:** `FastAPI + PostgreSQL` on cloud hosting ← `PySide6 (Qt)` on each Windows machine.
No database credentials ever exist on agent machines; everything is JWT + HTTPS.

---

## ✨ Features

### 🏢 Property Listings
- 4 deal types: **Sale / Pre-sale / Rent / Full Mortgage** — each with its own detail fields
- **Jalali (Persian) calendar** across all forms and reports
- **Photo gallery** per listing (up to 10 per upload, auto thumbnails)
- **Card view (Divar-style)** + table view — with big price badge, urgency, photo counter
- **Urgency flag**: "🔥 Urgent" checkbox + deadline date + "Urgent only" filter
- Standard amenities (elevator/parking) + **custom tag amenities**
- **Duplicate/similar warning** (owner phone or city+address) — shows registering agent, non-blocking
- **Live multi-column search** with highlighting + `Ctrl+F` + **global search `Ctrl+K`** (listings + client requests)
- Full structured filters (city, district, area, rooms, price, property type) + **saved filter chips** (agent proposes → admin approves)
- Sorting by date / area / price / contract end
- **Unlimited amounts**: money columns are NUMERIC — no artificial caps
- **Location link** (Google Maps share) + open address in Maps from any row
- Real pagination — nothing silently hidden (no 500-row cap)

### 💰 Commission Accounting (admin only)
- **Deals** on any listing with commission % (manual or agent default)
- **Finalization** with confirmation guard → listing archived (sold / rented)
- **Partner deals between two agents** 🤝: percentage split (e.g. 25+15 of 40);
  at finalization each agent's share becomes an independent ledger record
- **Payments in/out** with Jalali date, note and **photo receipt** — per-agent selection on partner deals
- **Balances tab**: earned − net paid per agent
- **Full individual ledger** (deals + payments + receipts + totals) for every agent and the admin
- **PDFs**: per-deal settlement, all balances, individual ledger, all ledgers (one file), and an
  **official contract** with an editable text template (`contract_template.txt`)
- **Deals Excel export** (RTL, styled header)

### 🙋 Client Requests + Auto-Matching
- Record client requests (type, city, district, area, rooms, **budget cap**)
- **"Matching listings"** button: active properties matching the criteria
- **Automatic notification 🎯**: when a new listing is added and matches open requests,
  each request owner is notified — "the shop that brings its own customers"
- **Client pipeline**: 🆕 New → 📞 Contacted → 🏠 Visited → 🤝 Negotiation → ✅ Won / ❌ Lost
  + stage counters on the dashboard

### ✅ Daily Follow-ups & Notifications
- Daily tasks with **Jalali date + time**, linked to listings
- Overdue / today / upcoming / done filters
- **"Stale listings" report**: active listings with no follow-up in the last N days
- **Smart notification bell**: contract deadlines, deal finalization, payments, chat,
  filter proposals, and expiration decisions
- **Automatic urgency alert on login** (contracts ending within 7 days)
- **Old-listing scan** by admin → the listing owner decides: expire or keep

### 💬 Internal Chat + Bot
- Private user-to-user chat (two-tone bubbles, **per-user colored avatar**, unread counters)
- **Melkyar bot**: auto-answers to FAQs — admin manages Q&A from the UI

### 🗄️ Archive & Expiration
- Triple archive: **inactive / sold / rented** — owner history kept forever
- One-click reactivation
- Auto-expiration decided by the listing owner (never silent deletion)

### 📊 Dashboard
- 11 clickable stat cards (jump straight to the relevant filter)
- 12-month finalized-deals chart + commission share per agent
- Client pipeline counters

### ⚙️ UX
- **Dark/light theme** + **font size slider 12–24 px** — persistent
- Full RTL + **Vazirmatn** font
- Toasts for success messages (no OK clicking) — modals only for errors/confirmations
- Table spinners while fetching + helpful empty states
- Sidebar width and chart fonts scale with the user's font size

### 🔐 Security
- **JWT** with 8h expiry + `token_version`: password reset / deactivation instantly revokes all sessions
- **Account lockout**: 3 wrong passwords = 2-minute lock (admin unlimited)
- **Optimistic locking**: concurrent edits → 409, not silent overwrite
- Agent/admin access enforced **server-side**
- `/docs` and `/openapi.json` fully disabled in production
- **Structured file logging** + database operation history (who, when, what)
- DB credentials exist only on the server; clients hold only an in-RAM JWT

### 💾 Backups & Updates
- **Automatic nightly compressed JSON backup at 02:30** — last 14 kept
- Manual backup + **backup download** by admin from the UI
- **Client auto-updates**: server hosts `/version` + installer;
  the client offers the new version on launch
- Chunked installer upload (resilient to unstable networks) by admin

---

## ☁️ Server Deployment (Runflare / Docker)

```bash
git clone https://github.com/tinatvk81/melkyar_application_new.git melkyar
cd melkyar

# Environment variables (panel or .env):
#   POSTGRES_HOST / PORT / DB / USER / PASSWORD
#   SECRET_KEY (long & random), DEBUG=false
#   APP_VERSION=1.5.0, INSTALLER_FILENAME=RealEstateApp-Setup-1.5.0.exe

docker compose up -d --build
docker compose exec server alembic upgrade head
docker compose exec server python scripts/init_admin.py   # interactive, once
curl https://<domain>/health   # {"status":"ok", ...}
```

**Deployment notes:**
- Startup micro-migration (`ensure_columns`) auto-adds new columns, enum values,
  and converts money columns to NUMERIC
- Persistent disks for: `server/media` (photos/receipts/backups), `server/static_installers`, `server/logs`
- Keep the database's **remote access OFF** — only the API is network-exposed
- Never commit `.env`

## 💻 Windows Client

**From source (development):**
```bash
cd client
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**Production install:** download `RealEstateApp-Setup-x.y.z.exe` from the server.
Server address is set in the login window → "Connection settings" (persisted in settings.json).
Auto-update: on launch, the client offers new versions with one click.

**Building the installer:**
```bash
cd client
build_installer.bat     # PyInstaller → dist\RealEstateApp.exe
upload_installer.bat    # chunked upload to the host (final name from INSTALLER_FILENAME)
```

## 🧱 Project Structure

```
client/                       PySide6 — HTTPS + JWT only
  main.py                     entry point + software-rendering env
  api_client.py               HTTP layer (shared Session — TLS reuse)
  settings_manager.py         settings.json next to the exe
  updater.py                  auto-update check
  ui/                         all tabs & dialogs (see Persian README)
  resources/fonts/            Vazirmatn
server/                       FastAPI + SQLAlchemy + Alembic + PostgreSQL
  app/api/routes/             auth, properties, property_images, users, reports,
                              deals, client_requests, follow_ups, notifications,
                              filter_presets, chat, bot, activity_logs,
                              import_excel, version, installers, backups
  app/models/                 User, Property, Deal, CommissionPayment, ...
  app/db/ensure_columns.py    idempotent startup micro-migration
  app/services/               PDFs, backup, sms, activity_log
  alembic/                    migrations
  static_installers/          client installer (persistent disk)
  contract_template.txt       official contract template (editable, no code)
```

## 🧪 Tests
```bash
cd server && pytest    # unit tests (auth, access, filters, locking, ...)
```

## 🗺 Roadmap
Decision history: `roadmap-v2.md` → `roadmap-v3.md` → **`roadmap-v4.md` (current — complete)**

## 🙏 Credits
Font: [Vazirmatn](https://github.com/rastikerdar/vazirmatn) (OFL)
```