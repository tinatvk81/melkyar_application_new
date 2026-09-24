

This document supersedes roadmap-v2 and v3. All 12 v3 promises are implemented,
plus 20 new features driven by real-world usage, plus a full infrastructure
migration from "office server / WSL" to Runflare cloud hosting.

> **Melkyar** is a multi-user desktop system for real-estate offices. Agents run a lightweight desktop app that connects over HTTPS to a cloud server; the admin sees everything while each agent sees only their own listings — enforced server-side, not in the client. It covers the full real-estate workflow: listings (sale/rent/mortgage/pre-sale) with photos, Persian calendar, maps and urgency flags; fast search and a Divar-style card view; duplicate-listing warnings; automatic matching between new listings and client requests with notifications; daily follow-ups and contract-expiry alerts; commission accounting including two-agent partner deals with percentage splits and photo receipts; internal chat and a FAQ bot; PDF/Excel outputs (official contract, settlement, individual ledgers); automatic nightly backups with admin download; and automatic app updates for every user delivered by the server itself. Security: JWT with instant revocation, account lockout, closed API docs in production, and database credentials kept server-side only.


*********

## Part A — roadmap-v3 commitments: all done ✅

| # | v3 item | Status |
|---|---|---|
| 1 | Real pagination (drop the 500 cap) | ✅ page/page_size/total + pagination bar |
| 2 | Archive & restore | ✅ triple archive + restore + owner-confirmed expiration |
| 3 | Real ActivityLog | ✅ recorded on every action + paginated history tab |
| 4 | Free-text search | ✅ live multi-column with highlight + Ctrl+F |
| 5 | Sorting | ✅ server sort_by + card-view sorting |
| 6 | External server settings | ✅ settings.json + "Connection settings" dialog |
| 7 | Clear session expiry | ✅ centralized 401 handler |
| 8 | Optimistic locking | ✅ version column + 409 |
| 9 | Excel import duplicates | ✅ similar-warning (form + import) |
| 10 | Structured file logging | ✅ setup_logging |
| 11 | Urgency alert on login | ✅ auto dialog for <7-day contracts |
| 12 | /docs closed | ✅ DEBUG=false |

## Part A2 — Cloud infrastructure (Runflare) ✅

- API service (Docker, gunicorn + UvicornWorker) + managed PostgreSQL 16
- Env vars on the panel; postStart = alembic + ensure_columns
- Idempotent micro-migration: new columns, new enum values, money → NUMERIC
- Persistent disks: media (photos/receipts/backup) • static_installers • logs
- Database never exposed to the internet; only the API
- PyPI mirror (Tsinghua) in the Dockerfile — direct PyPI unreachable from Iranian networks

## Part B — 20 new v1.5 features ✅

1. **Price & per-m² columns** — server builds `price_display`/`price_per_m2_display` (deal-type aware); table and cards share one source
2. **Card price badge** — correct rent format ("deposit X / rent Y")
3. **Colored deal-status badges** — green/yellow/red
4. **Toasts** — 1.5s + fade; modals only for errors/confirmations
5. **Table spinners** — transparent overlay, show/hide
6. **Empty states** — notifications 📭, dashboard chart
7. **Call/WhatsApp/Maps** — context menu from list row + buttons on cards
8. **Urgency** — `urgent_until` (Date) + 🔥 badge + server-side `urgent_only` filter (urgent or contract ≤7 days)
9. **Photo badge + card call button** — one-click copy
10. **location_url** — form field + "🗺 Map" button
11. **Rent↔Mortgage calculator** — editable factor in-dialog (default 30, stored in settings.json)
12. **Auto-match notifications** — POST /properties/notify-matches/{id}; matching logic shared with request_matches
13. **Global search Ctrl+K** — listings (server search) + requests (client filter); Enter opens
14. **Deals Excel export** — /deals/export/excel (openpyxl, RTL)
15. **Client pipeline** — new enum (open/contacted/visited/negotiation/won/lost) + stage combo + dashboard counters
16. **Stale listings** — GET /properties/stale (active, no follow-up for N days) + dialog with double-click
17. **rented** — new PropertyStatus; rent/mortgage finalization → rented (not sold); unfinalize reverses both
18. **Backups** — gzip JSON service (12 tables) + 02:30 cron + /backups/run|list|download + admin UI
19. **Chat avatars** — stable color derived from sender name
20. **Shared HTTP Session** — requests.Session; single TLS handshake (fixed ~3s/request slowness)

## Part C — other important fixes of this cycle ✅

- **Unlimited amounts**: BigInteger → NUMERIC (26-digit entry tested)
- **500-crash fix**: missing model columns (commission_percent, kind) — micro-migration
- **Circular import fix** properties↔client_requests (local import)
- **RTL time + compact Jalali date** (removed global spinbox min-width)
- **Chunked installer upload** /installers/chunk + /finalize (5 chunks, retry)
- **New agents appear in chat**, font-scaled sidebar, currentCellChanged signal fix
- **Chart fonts** scale with user font size
- **Cards refresh after save** (_reload_all)

## Part D — operational lessons learned 📚

- K8s CrashLoopBackOff = failed postStart or a terminating main command — read the log
- Never retype a DB password from a screenshot; use the URI copy button
- Env vars only reach *new* pods — always redeploy after changing them
- Windows SmartScreen: unsigned exe = "unknown" — More info → Run anyway
- Measure perceived slowness with `curl -w` first; TLS handshake ≠ app slowness

## Part E — v1.5+ backlog (proposed)

- [ ] Software-rendering env in next release (fixes white/frozen windows on some GPUs)
- [ ] Real two-way "typing…" (POST /chat/typing + TTL)
- [ ] Restore JSON backup from UI (currently download-only)
- [ ] Auto-prune activity_logs/chat_messages (Storage now 38% — not urgent)
- [ ] rented filter in the archive UI (endpoint ready; UI pending)
- [ ] Code signing if distribution widens
- [ ] Telegram/SMS notification channel (future need)
```
