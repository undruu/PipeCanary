# PipeCanary — Suggested Next Steps

**Based on:** PipeCanary Master Project Plan
**Current State:** Phase 1 (Foundation) ~85% complete
**Date:** February 2026

---

## Where We Stand

Phase 1 delivered solid foundational infrastructure: FastAPI scaffolding, Docker Compose, database schema with Alembic migrations, Snowflake connector, schema drift engine, anomaly detector, Slack notifier, and basic API routes. However, several Phase 1 items remain incomplete and all Celery monitoring tasks are still stubs.

### Phase 1 Completion Checklist

| Task | Status | Notes |
|---|---|---|
| Project scaffolding (FastAPI, Celery, PostgreSQL, Docker) | Done | All services running in docker-compose |
| Database schema + Alembic migrations | Done | 8 tables, indexes, FKs all in place |
| Auth integration (Clerk/Auth0) | **Not started** | `get_current_user` is a placeholder dependency |
| Snowflake connector | Done | Full implementation with all 6 interface methods |
| Schema snapshot engine | Done | `SchemaEngine.detect_drift()` with column-level diffing |
| Schema drift alerting logic | Partial | Detection works, but not wired into Celery tasks |
| Basic Slack notification | Done | `SlackNotifier` with Block Kit formatting |
| Unit/integration test foundation | Minimal | Only 1 health endpoint test exists |

---

## Recommended Next Steps (Priority Order)

### 1. Wire up Celery monitoring tasks (HIGH — Phase 1/2 bridge)

**File:** `backend/app/tasks/monitoring.py`

All four task functions are stubs with TODO comments. This is the critical gap that prevents the end-to-end loop (connect → detect → alert) from working.

**What to implement:**
- `run_scheduled_checks()` — Query active `monitored_tables`, dispatch per-table tasks
- `run_schema_check(table_id)` — Load connection, instantiate connector, call `SchemaEngine.detect_drift()`, create alert + send Slack notification
- `run_row_count_check(table_id)` — Get row count, store `CheckResult`, fetch 14-day history, run `AnomalyDetector.detect_row_count_anomaly()`, create alert if needed
- `run_null_rate_check(table_id)` — Get null counts per column, calculate rates, store results, run `AnomalyDetector.detect_null_rate_anomaly()`, create alert if needed

**Key challenge:** Celery tasks are synchronous but the connectors and database are async. You'll need an async bridge (e.g. `asyncio.run()` or `asgiref.sync.async_to_sync`).

**Estimated effort:** 10–12 hours

---

### 2. Wire up live connector in API endpoints (HIGH)

**Files:** `backend/app/api/connections.py`

Two endpoints return hardcoded/placeholder responses instead of using the actual Snowflake connector:
- `POST /connections/{id}/test` — Always returns `success: true` without testing anything (line 62–70)
- `GET /connections/{id}/tables` — Returns `{"tables": [], "message": "Connector not yet configured"}` (line 86)

**What to implement:**
- Instantiate the correct `WarehouseConnector` subclass based on `connection.type`
- Call `connector.test_connection()` and return actual results
- Call `connector.get_tables()` and return actual table listings

**Estimated effort:** 4–6 hours

---

### 3. Implement auth integration (HIGH)

**File:** `backend/app/api/deps.py`

The `get_current_user` dependency is a stub. Without real auth, the API is completely open.

**What to implement:**
- Integrate Clerk or Auth0 JWT validation
- Decode and verify tokens in the `get_current_user` dependency
- Create/sync user records on first login
- API key generation for programmatic access

**Estimated effort:** 8 hours (per master plan)

---

### 4. Expand test coverage (MEDIUM)

**Current state:** 1 test (health endpoint). Zero coverage on the core business logic.

**Priority tests to add:**
- `test_anomaly_detector.py` — Unit tests for z-score detection, null rate detection, edge cases (empty data, single data point, constant values)
- `test_schema_engine.py` — Unit tests for schema diffing (added/removed/changed columns, no-change case)
- `test_snowflake_connector.py` — Mock-based tests for connector methods
- `test_slack_notifier.py` — Mock httpx to verify Slack message formatting
- `test_api_connections.py` — Integration tests for connection CRUD and test endpoints
- `test_api_alerts.py` — Integration tests for alert listing, filtering, and status updates

**Estimated effort:** 6–8 hours

---

### 5. BigQuery connector (MEDIUM — Phase 2)

**File to create:** `backend/app/connectors/bigquery.py`

The master plan lists BigQuery as a P0 (Must Have) for MVP. The abstract `WarehouseConnector` base class is already defined, so this is a straightforward implementation.

**What to implement:**
- Service account authentication via `google-cloud-bigquery` SDK
- All 6 interface methods: `test_connection`, `get_tables`, `get_schema`, `get_row_count`, `get_null_counts`, `get_cardinality`
- Use `INFORMATION_SCHEMA` for metadata queries (similar pattern to Snowflake connector)

**Estimated effort:** 10 hours (per master plan)

---

### 6. Email notification integration (MEDIUM — Phase 2)

**File to create:** `backend/app/notifications/email.py`

The master plan calls for SendGrid-based email alerts alongside Slack.

**What to implement:**
- `EmailNotifier` class following same pattern as `SlackNotifier`
- HTML email template for alert notifications
- Digest mode support (batch multiple alerts into one email)
- Wire into the notification dispatch in Celery tasks

**Estimated effort:** 6 hours (per master plan)

---

### 7. Scheduling configuration API (LOW — Phase 2)

Per-table check frequency settings. The `monitored_tables` table already has a `check_frequency` column, but there's no API to update it and `run_scheduled_checks` doesn't yet filter by frequency.

**Estimated effort:** 4 hours (per master plan)

---

## Phase Summary & Timeline

| Priority | Task | Phase | Est. Hours |
|---|---|---|---|
| 1 | Wire up Celery monitoring tasks | 1/2 bridge | 10–12 |
| 2 | Wire up live connector in API endpoints | 1 finish | 4–6 |
| 3 | Implement auth integration | 1 finish | 8 |
| 4 | Expand test coverage | 1 finish | 6–8 |
| 5 | BigQuery connector | 2 | 10 |
| 6 | Email notifications (SendGrid) | 2 | 6 |
| 7 | Scheduling configuration API | 2 | 4 |
| **Total** | | | **48–54 hours** |

Completing items 1–4 finishes Phase 1 and delivers the core end-to-end loop: **connect warehouse → run scheduled checks → detect anomalies → send Slack alerts → view in API**. Items 5–7 are the beginning of Phase 2 (Core Monitoring, Weeks 4–6 per the master plan).

---

## After That: Phase 3 & 4 at a Glance

**Phase 3 (Weeks 7–9): Dashboard & UX** — React dashboard pages (connection management, table browser with health sparklines, alert feed), onboarding wizard, Databricks connector, notification preferences UI.

**Phase 4 (Weeks 10–12): Billing & Launch** — Stripe subscriptions, tier enforcement middleware, landing page, production deployment (AWS ECS/Railway), Sentry logging, security hardening, beta testing with 3–5 pilot customers.
