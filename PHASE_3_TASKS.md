# PipeCanary — Phase 3 Tasks: Dashboard & UX

**Based on:** PipeCanary Master Project Plan
**Current State:** Phase 1 & 2 complete; Phase 3 (Dashboard & UX) ready to begin
**Date:** February 2026

---

## Where We Stand

Phases 1 and 2 delivered the complete backend infrastructure: FastAPI with JWT/API-key auth, PostgreSQL with 9 tables and Alembic migrations, Snowflake and BigQuery connectors, Celery-based scheduled monitoring (schema drift, row count, null rate), statistical anomaly detection (z-score, percentage change), Slack and SendGrid email notifications, and a full REST API with filtering/pagination. The end-to-end backend loop works: **connect warehouse → run scheduled checks → detect anomalies → create alerts → send notifications**.

The React frontend exists but is entirely static — three placeholder pages with hardcoded zeros and empty states. The API client is defined but unused. There is no auth integration, no state management, no forms, no modals, no charts, and no reusable component library. Phase 3 transforms these shells into a fully functional, data-driven dashboard.

### Phase 1 & 2 Completion Checklist

| Task | Status | Notes |
|---|---|---|
| Project scaffolding (FastAPI, Celery, PostgreSQL, Docker) | Done | All services running in docker-compose |
| Database schema + Alembic migrations | Done | 9 tables (incl. api_keys), indexes, FKs |
| JWT auth + API key authentication | Done | Register, login, refresh, API key CRUD |
| Snowflake connector | Done | Full 6-method implementation with key-pair auth |
| BigQuery connector | Done | Full 6-method implementation with service account auth |
| Schema drift detection engine | Done | `SchemaEngine.detect_drift()` with column-level diffing |
| Anomaly detector (z-score, null rate) | Done | Handles edge cases; configurable thresholds |
| Celery monitoring tasks | Done | `run_schema_check`, `run_row_count_check`, `run_null_rate_check` |
| Scheduling configuration API | Done | Per-table frequency; dispatch filters by schedule |
| Slack notifications | Done | `SlackNotifier` with Block Kit formatting |
| Email notifications (SendGrid) | Done | HTML templates, digest mode support |
| Alert management API | Done | List, acknowledge, resolve, snooze with filtering |
| Test coverage | Done | 12 test files across connectors, engines, notifiers, API |
| React frontend scaffolding | Done | 3 static pages, Layout component, API client (unused) |

---

## Phase 3 Tasks (Priority Order)

### 1. Frontend auth integration and state management (HIGH)

**Files:** `frontend/src/` — new files in `hooks/`, `context/`, and `pages/`

Before any page can load real data, the frontend needs authentication and global state. Without this, every other task is blocked.

**What to implement:**

- **Auth context provider** (`context/AuthContext.tsx`) — Store JWT tokens, current user, login/logout state
- **Login and register pages** (`pages/Login.tsx`, `pages/Register.tsx`) — Forms calling `POST /api/v1/auth/login` and `POST /api/v1/auth/register`
- **Token management** — Store access/refresh tokens in memory (or localStorage), attach `Authorization: Bearer` header to all API requests, auto-refresh on 401
- **Protected route wrapper** — Redirect unauthenticated users to `/login`
- **Update `api/client.ts`** — Inject auth token into all requests; add `login()`, `register()`, `refreshToken()`, `getMe()` methods
- **Update `App.tsx` routing** — Add `/login`, `/register` routes; wrap authenticated routes in protection
- **User menu in Layout** — Show current user name/email in nav bar with logout action

**Key challenge:** Token refresh logic must handle race conditions when multiple requests fail simultaneously with 401.

**Estimated effort:** 8–10 hours

---

### 2. React dashboard: Connection management page (HIGH)

**Files:** `frontend/src/pages/Connections.tsx`, new components in `components/`

The current Connections page is a static empty state with a non-functional "Add Connection" button. This needs to become a fully interactive CRUD interface.

**What to implement:**

- **Connection list** — Fetch and display all connections with status badges (pending/active/failed), type icons (Snowflake/BigQuery/Databricks), and last-tested timestamp
- **Add Connection modal/dialog** — Multi-step form:
  1. Select warehouse type (Snowflake, BigQuery, Databricks)
  2. Enter credentials (dynamic form fields per warehouse type)
  3. Test connection → show success/failure with `POST /connections/{id}/test`
  4. Save and redirect to table selection
- **Connection detail view** — Show connection config, status, list of monitored tables under this connection
- **Edit/delete connection** — Update credentials, remove connection (with confirmation)
- **Test connection action** — Re-test existing connections from the list view
- **Reusable components to build:**
  - `Modal.tsx` — Generic modal/dialog wrapper
  - `StatusBadge.tsx` — Color-coded status indicator (pending=yellow, active=green, failed=red)
  - `Button.tsx` — Consistent button styles (primary, secondary, danger)
  - `FormField.tsx` — Labeled input with validation error display

**Backend endpoints used:**
- `POST /api/v1/connections` — Create
- `POST /api/v1/connections/{id}/test` — Test
- `GET /api/v1/connections/{id}/tables` — List tables for a connection

**Estimated effort:** 12 hours

---

### 3. React dashboard: Table browser and health overview (HIGH)

**Files:** `frontend/src/pages/Dashboard.tsx`, `pages/Tables.tsx` (new), new components

This is the core value page — the at-a-glance health overview that tells users whether their data is healthy. The current Dashboard shows three hardcoded zeros.

**What to implement:**

- **Dashboard summary cards** — Replace hardcoded zeros with live data:
  - Active Connections count
  - Monitored Tables count
  - Open Alerts count (with severity breakdown)
  - Last check timestamp
- **Table browser page** (`/tables`) — List all monitored tables across all connections with:
  - Health status indicator per table (healthy/warning/critical based on open alerts)
  - Latest row count with sparkline (mini trend chart from recent `check_results`)
  - Last checked timestamp
  - Check frequency badge
  - Active/paused toggle
- **Table detail view** (`/tables/:id`) — Deep dive into a single table:
  - Current schema (columns, types, nullable) from latest `schema_snapshots`
  - Schema change history timeline from `GET /tables/{id}/schema/history`
  - Row count trend chart (14-day history from check_results)
  - Null rate per column (bar chart or heatmap)
  - Recent alerts for this table
  - Edit check frequency (`PATCH /tables/{id}/schedule`)
- **Table selection flow** — After connecting a warehouse, list available tables (`GET /connections/{id}/tables`) and let users select which to monitor (`POST /tables/monitor`)
- **Reusable components to build:**
  - `SparklineChart.tsx` — Tiny inline trend chart (use SVG or a lightweight lib like `recharts`)
  - `HealthIndicator.tsx` — Green/yellow/red dot with tooltip
  - `DataTable.tsx` — Sortable, filterable table component
  - `EmptyState.tsx` — Reusable empty state with icon and CTA

**Backend endpoints used:**
- `GET /api/v1/tables/{id}/health` — Table health summary
- `GET /api/v1/tables/{id}/schema/history` — Schema snapshots
- `GET /api/v1/connections/{id}/tables` — Available tables in warehouse
- `POST /api/v1/tables/monitor` — Start monitoring selected tables
- `GET /api/v1/tables/{id}/schedule` — Current schedule
- `PATCH /api/v1/tables/{id}/schedule` — Update frequency/active status

**Note:** The backend currently doesn't have a "list all monitored tables" endpoint. You'll need to add `GET /api/v1/tables` to the tables router to return all monitored tables for the user's org with health summary data.

**Estimated effort:** 14 hours

---

### 4. React dashboard: Alert feed and detail view (HIGH)

**Files:** `frontend/src/pages/Alerts.tsx`, new components

The current Alerts page has non-functional filter buttons and a static empty state. It needs to become a real-time alert feed.

**What to implement:**

- **Alert feed** — Paginated list of alerts from `GET /api/v1/alerts` with:
  - Alert type icon/color (schema_drift=purple, row_count=blue, null_rate=orange)
  - Severity badge (warning=yellow, critical=red)
  - Status badge (open, acknowledged, resolved, snoozed)
  - Table name and connection name for context
  - Relative timestamp ("2 hours ago")
  - Truncated details preview
- **Working filter controls** — Wire up the existing filter buttons:
  - Status filter (All, Open, Acknowledged, Resolved)
  - Type filter (Schema Drift, Row Count, Null Rate)
  - Table filter (dropdown of monitored tables)
  - Date range filter
- **Alert detail panel** — Click an alert to expand/open detail view showing:
  - Full `details_json` rendered in a human-readable format:
    - Schema drift: show column diff (added/removed/changed columns in a table)
    - Row count: show expected range vs. actual value, z-score
    - Null rate: show column name, baseline rate vs. current rate
  - Action buttons: Acknowledge, Resolve, Snooze
  - Link to affected table's detail page
- **Bulk actions** — Select multiple alerts and acknowledge/resolve in batch
- **Pagination** — "Load more" or infinite scroll using `limit` and `offset` params
- **Reusable components to build:**
  - `AlertCard.tsx` — Individual alert display card
  - `FilterBar.tsx` — Reusable filter strip with dropdown/chip selectors
  - `Pagination.tsx` — Load more / page navigation controls
  - `RelativeTime.tsx` — "2 hours ago" time display (or use a lib like `date-fns`)

**Backend endpoints used:**
- `GET /api/v1/alerts?status=...&alert_type=...&table_id=...&limit=...&offset=...`
- `PATCH /api/v1/alerts/{id}` — Update status

**Estimated effort:** 10 hours

---

### 5. Onboarding wizard (MEDIUM)

**Files:** `frontend/src/pages/Onboarding.tsx`, `components/wizard/`

The master plan calls for a guided 3-step setup flow to get new users from signup to their first alert in under 10 minutes.

**What to implement:**

- **Step 1: Connect Warehouse** — Simplified connection form (reuse connection creation from Task 2) with warehouse type selection tiles and credential input
- **Step 2: Select Tables** — Fetch tables from the connected warehouse, display as a checkbox list with schema grouping, let user select which tables to monitor
- **Step 3: Configure Alerts** — Set check frequency (with sensible defaults), configure Slack webhook URL and/or email for notifications, show preview of what alerts will look like
- **Progress indicator** — Step indicator bar showing current step (1/2/3) with back/next navigation
- **Completion state** — Success screen with "Go to Dashboard" CTA showing that monitoring is now active
- **Auto-redirect for new users** — After registration, redirect to onboarding if user has zero connections
- **Reusable components to build:**
  - `StepIndicator.tsx` — Numbered step progress bar
  - `WizardLayout.tsx` — Centered card layout for wizard steps

**Backend endpoints used (in sequence):**
1. `POST /api/v1/connections` → `POST /api/v1/connections/{id}/test`
2. `GET /api/v1/connections/{id}/tables?schema=...`
3. `POST /api/v1/tables/monitor` → `PUT /api/v1/notifications/config`

**Estimated effort:** 8 hours

---

### 6. Databricks connector implementation (MEDIUM)

**File to create:** `backend/app/connectors/databricks.py`

The master plan lists Databricks as P1 (Should Have). The connector factory currently only supports `snowflake` and `bigquery`. The abstract `WarehouseConnector` base class is defined, so this follows the same pattern.

**What to implement:**

- **Authentication** — Support Databricks personal access token and OAuth (M2M) via `databricks-sql-connector` SDK
- **Connection config** — `server_hostname`, `http_path`, `access_token`, optional `catalog` (Unity Catalog) and `schema`
- **All 6 interface methods:**
  - `test_connection()` — Execute `SELECT 1` via SQL Warehouse
  - `get_tables(schema)` — Query `information_schema.tables` in the specified catalog/schema
  - `get_schema(table)` — Query `information_schema.columns` for column metadata
  - `get_row_count(table)` — `SELECT COUNT(*) FROM {catalog}.{schema}.{table}`
  - `get_null_counts(table, columns)` — `SUM(CASE WHEN col IS NULL ...)` pattern
  - `get_cardinality(table, columns)` — `COUNT(DISTINCT col)` pattern
- **Register in connector factory** — Add `"databricks"` to `_CONNECTOR_TYPES` and instantiation logic in `connectors/__init__.py`
- **Unity Catalog support** — Handle 3-level namespace (`catalog.schema.table`) for Databricks
- **Tests** — Mock-based unit tests following the pattern in `tests/test_snowflake_connector.py` and `tests/test_bigquery_connector.py`

**Dependencies to add:** `databricks-sql-connector` in `requirements.txt`

**Estimated effort:** 10 hours

---

### 7. Notification preferences UI (MEDIUM)

**Files:** `frontend/src/pages/Settings.tsx` (new), `components/`

Users need a way to manage their notification channels and preferences from the web UI.

**What to implement:**

- **Settings page** (`/settings`) — New route with tab navigation:
  - **Notifications tab:**
    - List existing notification configs (Slack webhooks, email addresses)
    - Add new Slack webhook with test button (sends a test message)
    - Add/remove email recipients
    - Toggle notifications on/off per channel
    - Configure filters: which alert types and severities to receive per channel
  - **API Keys tab:**
    - List existing API keys (show prefix, name, last used, created date)
    - Create new API key with name (show the full key once, then mask it)
    - Revoke API keys with confirmation
  - **Profile tab:**
    - Display current user info (name, email)
    - Current plan tier and organization name
- **Add Settings link to navigation** — Update `Layout.tsx` nav items to include Settings
- **Reusable components to build:**
  - `Tabs.tsx` — Tab navigation component
  - `Toggle.tsx` — On/off switch for enable/disable states
  - `CopyableField.tsx` — Text field with copy-to-clipboard button (for API keys)
  - `ConfirmDialog.tsx` — "Are you sure?" confirmation modal

**Backend endpoints used:**
- `PUT /api/v1/notifications/config` — Create/update notification config
- `GET /api/v1/auth/api-keys` — List API keys
- `POST /api/v1/auth/api-keys` — Create API key
- `DELETE /api/v1/auth/api-keys/{id}` — Revoke API key
- `GET /api/v1/auth/me` — Current user info

**Note:** The backend currently doesn't have a `GET /api/v1/notifications/config` endpoint to list existing configs. You'll need to add this to the notifications router.

**Estimated effort:** 6 hours

---

### 8. Backend API additions for frontend (LOW)

**Files:** `backend/app/api/tables.py`, `backend/app/api/notifications.py`, `backend/app/schemas/`

Several frontend features require minor backend additions that don't exist yet.

**What to implement:**

- **`GET /api/v1/tables`** — List all monitored tables for the user's org with basic health info (open alert count, last checked, status). Supports filtering by `connection_id` and `is_active`.
- **`GET /api/v1/connections`** — List all connections for the user's org (currently no list endpoint exists).
- **`DELETE /api/v1/connections/{id}`** — Delete a connection (cascade to monitored_tables or reject if tables exist).
- **`GET /api/v1/notifications/config`** — List all notification configs for the user's org.
- **`GET /api/v1/dashboard/summary`** — Aggregate endpoint returning connection count, monitored table count, open alert count, and last check timestamp in a single call (avoids multiple round-trips from the Dashboard page).
- **Add Pydantic response schemas** as needed for the new endpoints.

**Estimated effort:** 4–6 hours

---

### 9. Frontend polish and loading states (LOW)

**Files:** Various frontend components

After the core features are built, polish the UX to feel production-ready.

**What to implement:**

- **Loading skeletons** — Shimmer/placeholder UI while data loads on Dashboard, Connections, Tables, and Alerts pages
- **Error boundaries** — Catch and display friendly error messages when API calls fail
- **Toast notifications** — Success/error feedback for actions (connection created, alert acknowledged, API key copied, etc.)
- **Empty states** — Consistent, helpful empty states with icons and CTAs (e.g., "No tables monitored yet. Add a connection to get started.")
- **Responsive design** — Ensure all pages work on tablet and mobile widths
- **Keyboard shortcuts** — `Esc` to close modals, `Enter` to submit forms
- **Page titles** — Update `document.title` per route for browser tab clarity
- **Reusable components to build:**
  - `Skeleton.tsx` — Loading placeholder component
  - `Toast.tsx` + `ToastContext.tsx` — Toast notification system
  - `ErrorBoundary.tsx` — React error boundary with fallback UI

**Estimated effort:** 6–8 hours

---

## Phase 3 Summary & Timeline

| Priority | Task | Est. Hours |
|---|---|---|
| 1 | Frontend auth integration and state management | 8–10 |
| 2 | Connection management page | 12 |
| 3 | Table browser and health overview | 14 |
| 4 | Alert feed and detail view | 10 |
| 5 | Onboarding wizard | 8 |
| 6 | Databricks connector | 10 |
| 7 | Notification preferences UI | 6 |
| 8 | Backend API additions for frontend | 4–6 |
| 9 | Frontend polish and loading states | 6–8 |
| **Total** | | **78–84 hours** |

Tasks 1–4 deliver the functional dashboard: **login → see connections → browse table health → manage alerts**. Task 5 adds the onboarding flow for new users. Task 6 adds the third warehouse connector. Tasks 7–9 round out the settings UI and polish.

**Recommended sequencing:**
- **Week 7:** Tasks 1 (auth) → 2 (connections) → 8 (backend additions) — these unblock everything else
- **Week 8:** Tasks 3 (tables/dashboard) → 4 (alerts) → 5 (onboarding) — core user-facing pages
- **Week 9:** Tasks 6 (Databricks) → 7 (settings) → 9 (polish) — completeness and quality

**Note:** This exceeds the master plan's 60-hour estimate by ~20 hours because the frontend is starting from static placeholders rather than partially implemented pages. The auth integration (Task 1) and backend API additions (Task 8) were not in the original estimate but are necessary prerequisites.

---

## After That: Phase 4 at a Glance

**Phase 4 (Weeks 10–12): Billing, Polish & Launch** — 72 hours

- Stripe subscription integration (checkout, webhooks, customer portal)
- Tier enforcement middleware (Free: 1 source/5 tables/daily, Pro: 3/unlimited/hourly, Team: 10/unlimited/15min)
- Landing page and marketing site (Next.js with pricing, features, signup CTA)
- Production infrastructure (AWS ECS Fargate or Railway, RDS, managed Redis)
- Logging, monitoring, and error tracking (Sentry, CloudWatch/DataDog)
- Security hardening (OWASP top 10, credential encryption audit, rate limiting)
- API documentation (auto-generated from FastAPI + supplemental guides)
- Beta testing with 3–5 pilot customers (feedback collection, critical bug fixes)
