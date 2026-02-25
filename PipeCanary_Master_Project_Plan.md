# PipeCanary — Master Project Plan

**Data Quality Alerts for Small Teams**
Version 1.0 | February 2026 | CONFIDENTIAL

---

## 1. Executive Summary

PipeCanary is a lightweight, affordable data quality observability platform targeting Series A–B startups with small data teams (5–20 people). The enterprise data observability market is projected to grow from $1.5B to $2.3B by 2030, yet current solutions like Monte Carlo, Great Expectations, and Soda cost $30K–$100K+/year, effectively locking out smaller organizations.

PipeCanary addresses this gap by delivering schema drift detection, anomaly alerts (row counts, null rates, cardinality), and Slack/email notifications with connectors for Snowflake, Databricks, and BigQuery—all at a fraction of the enterprise price point ($99–$299/mo).

| Target MVP | Price Range | Initial Market | Tech Stack |
|---|---|---|---|
| 12 weeks | Free – $299/mo | Series A–B startups | Python + React |

---

## 2. Product Vision & Scope

### Problem Statement

Small data teams at growth-stage startups face a critical blind spot: they lack automated data quality monitoring. Data issues—schema changes, missing values, row count anomalies—cascade silently through pipelines until they surface in dashboards, ML models, or customer-facing products. Existing enterprise tools are cost-prohibitive and overbuilt for teams of this size.

### Value Proposition

- **10-minute setup:** Connect your warehouse, select tables, get alerts immediately
- **Zero infrastructure:** Fully managed SaaS—no agents, sidecars, or dbt packages
- **Smart defaults:** Out-of-the-box anomaly detection with no manual threshold configuration
- **Team-friendly pricing:** Starting free, scaling to $299/mo for full team features

### MVP Feature Set (v1.0)

| Feature | Description | Priority |
|---|---|---|
| Schema Drift Detection | Detect added/removed/renamed columns, type changes | P0 — Must Have |
| Row Count Monitoring | Track table volumes; alert on anomalies vs. trailing average | P0 — Must Have |
| Null Rate Alerts | Monitor null percentage per column; flag unexpected spikes | P0 — Must Have |
| Slack Notifications | Real-time alerts to Slack channels with context | P0 — Must Have |
| Email Notifications | Digest and real-time email alerts | P1 — Should Have |
| Web Dashboard | View alert history, table health, connection status | P0 — Must Have |
| Snowflake Connector | Read-only connection via key-pair or OAuth | P0 — Must Have |
| BigQuery Connector | Service account-based read-only access | P0 — Must Have |
| Cardinality Monitoring | Track distinct value counts per column; detect unexpected cardinality shifts | P1 — Should Have |
| Databricks Connector | Unity Catalog / SQL Warehouse connection | P1 — Should Have |

### Out of Scope for v1.0

- Column-level lineage and impact analysis
- Custom SQL-based data quality checks
- dbt integration and test orchestration
- Data catalog / discovery features
- Multi-tenant role-based access control (beyond basic team features)

---

## 3. Technical Architecture

### System Overview

PipeCanary follows a modular, service-oriented architecture designed for simplicity in the MVP phase while allowing horizontal scaling as the customer base grows.

| Layer | Technology | Purpose |
|---|---|---|
| API Server | Python (FastAPI) | REST API, auth, business logic |
| Task Scheduler | Celery + Redis | Scheduled data quality checks |
| Database | PostgreSQL | User data, connections, alert history |
| Anomaly Engine | Python (scipy/numpy) | Statistical anomaly detection |
| Frontend | React + TypeScript + Tailwind | Dashboard UI |
| Notifications | Slack SDK, SendGrid | Alert delivery |
| Infrastructure | AWS (ECS Fargate) or Railway | Hosting, CI/CD |
| Auth | Clerk or Auth0 | User auth, team management |

### Data Flow

1. User connects warehouse via encrypted credentials (stored in AWS Secrets Manager or Vault)
2. Celery beat triggers scheduled checks (configurable: hourly, daily, or on cron)
3. Worker executes read-only queries against customer warehouse (schema introspection, `COUNT(*)`, null counts, distinct counts)
4. Results are compared against historical baselines using the anomaly engine
5. If anomaly detected: alert record created, notification dispatched via Slack/email
6. User views alert history and table health on the web dashboard

### Warehouse Connector Design

Each connector implements a common interface (Python abstract base class) with the following methods:

- `test_connection()` — Validates credentials and connectivity
- `get_tables(schema)` — Lists available tables in a schema
- `get_schema(table)` — Returns column names, types, and nullability
- `get_row_count(table)` — Returns current row count
- `get_null_counts(table, columns)` — Returns null count per column
- `get_cardinality(table, columns)` — Returns distinct value count per column

All queries are read-only. PipeCanary never writes to customer warehouses.

```python
from abc import ABC, abstractmethod
from typing import Any

class WarehouseConnector(ABC):
    """Base interface for all warehouse connectors."""

    @abstractmethod
    async def test_connection(self) -> bool:
        """Validate credentials and connectivity."""
        ...

    @abstractmethod
    async def get_tables(self, schema: str) -> list[dict[str, Any]]:
        """List available tables in a schema."""
        ...

    @abstractmethod
    async def get_schema(self, table: str) -> list[dict[str, Any]]:
        """Return column names, types, and nullability."""
        ...

    @abstractmethod
    async def get_row_count(self, table: str) -> int:
        """Return current row count."""
        ...

    @abstractmethod
    async def get_null_counts(self, table: str, columns: list[str]) -> dict[str, int]:
        """Return null count per column."""
        ...

    @abstractmethod
    async def get_cardinality(self, table: str, columns: list[str]) -> dict[str, int]:
        """Return distinct value count per column."""
        ...
```

### Anomaly Detection Approach

The MVP uses a simple but effective statistical approach:

- **Row counts:** Z-score against a 14-day trailing window. Alert if z > 3.0 (configurable).
- **Null rates:** Percentage change against 7-day average. Alert if delta > 2x baseline.
- **Cardinality:** Track distinct counts per column; alert on sudden drops (possible data loss) or spikes (possible duplication/corruption).
- **Schema drift:** Exact diff against last-known schema snapshot. Any change triggers an alert.

Post-MVP, the anomaly engine can be upgraded to use seasonal decomposition (STL), Prophet, or isolation forests for more sophisticated detection.

### Security Considerations

- All warehouse credentials encrypted at rest (AES-256) and in transit (TLS 1.3)
- Read-only warehouse access enforced at the connection level
- SOC 2 Type I target within 6 months of launch
- Data minimization: PipeCanary stores metadata only (counts, schema snapshots), never raw customer data
- Tenant isolation at the database row level (MVP), moving to schema-level isolation post-PMF

---

## 4. Development Phases

### Phase 1: Foundation (Weeks 1–3)

**Goal:** Core infrastructure, first warehouse connector, and basic schema monitoring.

| Task | Deliverable | Est. Hours |
|---|---|---|
| Project scaffolding (FastAPI, Celery, PostgreSQL) | Running dev environment with Docker Compose | 8 |
| Database schema design (users, connections, tables, checks, alerts) | Alembic migrations, ERD diagram | 6 |
| Auth integration (Clerk/Auth0) | Login, signup, API key generation | 8 |
| Snowflake connector implementation | Tested connector class with all interface methods | 12 |
| Schema snapshot engine | Store and diff table schemas on schedule | 10 |
| Schema drift alerting logic | Detect and record schema changes as alerts | 6 |
| Basic Slack notification | Send formatted alert messages to a webhook | 4 |
| Unit and integration test foundation | pytest suite, CI pipeline (GitHub Actions) | 6 |

**Phase 1 Total: ~60 hours**

### Phase 2: Core Monitoring (Weeks 4–6)

**Goal:** Full anomaly detection engine and second warehouse connector.

| Task | Deliverable | Est. Hours |
|---|---|---|
| Row count monitoring engine | Scheduled row count checks with historical storage | 10 |
| Null rate monitoring engine | Column-level null rate tracking and comparison | 10 |
| Cardinality monitoring engine | Distinct value count tracking per column with drift detection | 8 |
| Statistical anomaly detection (z-score, percentage change) | Configurable thresholds, anomaly flagging | 12 |
| BigQuery connector implementation | Tested connector with service account auth | 10 |
| Alert management API (list, acknowledge, resolve, snooze) | REST endpoints with filtering/pagination | 8 |
| Email notification integration (SendGrid) | Templated alert emails with context | 6 |
| Scheduling configuration API | Per-table check frequency settings | 4 |

**Phase 2 Total: ~68 hours**

### Phase 3: Dashboard & UX (Weeks 7–9)

**Goal:** User-facing dashboard, onboarding flow, and Databricks support.

| Task | Deliverable | Est. Hours |
|---|---|---|
| React dashboard: Connection management page | Add/edit/test warehouse connections | 12 |
| React dashboard: Table browser and health overview | Table list with health indicators, sparklines | 14 |
| React dashboard: Alert feed and detail view | Filterable alert timeline with context | 10 |
| Onboarding wizard (connect → select tables → configure alerts) | Guided 3-step setup flow | 8 |
| Databricks connector implementation | Unity Catalog + SQL Warehouse connector | 10 |
| Notification preferences UI | Configure Slack channels, email recipients, schedules | 6 |

**Phase 3 Total: ~60 hours**

### Phase 4: Billing, Polish & Launch (Weeks 10–12)

**Goal:** Stripe billing, tier enforcement, landing page, and production deployment.

| Task | Deliverable | Est. Hours |
|---|---|---|
| Stripe integration (subscriptions, webhooks, customer portal) | Working billing with plan enforcement | 14 |
| Tier enforcement (free: 1 source/5 tables, Pro, Team) | Middleware enforcing plan limits | 6 |
| Landing page and marketing site | Next.js site with pricing, features, signup CTA | 12 |
| Production infrastructure (AWS ECS or Railway, RDS, Redis) | Deployed, monitored production environment | 10 |
| Logging, monitoring, error tracking (Sentry, CloudWatch) | Observable production system | 6 |
| Security hardening and penetration testing checklist | Addressed OWASP top 10 for the app | 8 |
| Documentation (API docs, setup guides, FAQs) | Published docs site | 6 |
| Beta testing with 3–5 pilot customers | Feedback collected and critical bugs fixed | 10 |

**Phase 4 Total: ~72 hours**

---

## 5. Database Schema (Core Tables)

All tables include standard `created_at` and `updated_at` timestamps.

| Table | Key Columns | Type | Notes |
|---|---|---|---|
| `users` | id, email, name, plan_tier | Core | Synced from auth provider |
| `organizations` | id, name, owner_id, plan_tier | Core | Team billing entity |
| `connections` | id, org_id, type, credentials_ref | Core | Warehouse connections; creds in Secrets Manager |
| `monitored_tables` | id, connection_id, schema, table_name | Core | Tables selected for monitoring |
| `schema_snapshots` | id, table_id, columns_json, captured_at | Monitoring | Point-in-time schema records |
| `check_results` | id, table_id, check_type, value, measured_at | Monitoring | Row counts, null rates, cardinality per check run |
| `alerts` | id, table_id, type, severity, status, details_json | Alerting | Generated alerts with context |
| `notification_configs` | id, org_id, channel, destination, filters | Alerting | Where and how to deliver alerts |

### Alembic Migration (Initial)

```python
"""Initial schema migration."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid


def upgrade():
    # Users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("plan_tier", sa.String(50), nullable=False, server_default="free"),
        sa.Column("auth_provider_id", sa.String(255), unique=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Organizations
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plan_tier", sa.String(50), nullable=False, server_default="free"),
        sa.Column("stripe_customer_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Connections
    op.create_table(
        "connections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),  # snowflake, bigquery, databricks
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("credentials_ref", sa.String(512), nullable=False),  # Secrets Manager ARN
        sa.Column("config", JSONB),  # warehouse, database, schema defaults
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("last_tested_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Monitored Tables
    op.create_table(
        "monitored_tables",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("connection_id", UUID(as_uuid=True), sa.ForeignKey("connections.id"), nullable=False),
        sa.Column("schema_name", sa.String(255), nullable=False),
        sa.Column("table_name", sa.String(255), nullable=False),
        sa.Column("check_frequency", sa.String(50), server_default="daily"),  # hourly, daily, cron
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("connection_id", "schema_name", "table_name"),
    )

    # Schema Snapshots
    op.create_table(
        "schema_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("table_id", UUID(as_uuid=True), sa.ForeignKey("monitored_tables.id"), nullable=False),
        sa.Column("columns_json", JSONB, nullable=False),
        sa.Column("captured_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_schema_snapshots_table_captured", "schema_snapshots", ["table_id", "captured_at"])

    # Check Results
    op.create_table(
        "check_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("table_id", UUID(as_uuid=True), sa.ForeignKey("monitored_tables.id"), nullable=False),
        sa.Column("check_type", sa.String(50), nullable=False),  # row_count, null_rate, cardinality
        sa.Column("column_name", sa.String(255)),  # null for row_count
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("measured_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_check_results_table_type_measured", "check_results", ["table_id", "check_type", "measured_at"])

    # Alerts
    op.create_table(
        "alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("table_id", UUID(as_uuid=True), sa.ForeignKey("monitored_tables.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),  # schema_drift, row_count, null_rate, cardinality
        sa.Column("severity", sa.String(20), nullable=False, server_default="warning"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("details_json", JSONB, nullable=False),
        sa.Column("acknowledged_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("acknowledged_at", sa.DateTime),
        sa.Column("resolved_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_alerts_table_status", "alerts", ["table_id", "status"])

    # Notification Configs
    op.create_table(
        "notification_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),  # slack, email
        sa.Column("destination", sa.String(512), nullable=False),  # webhook URL or email
        sa.Column("filters", JSONB),  # severity, type filters
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade():
    op.drop_table("notification_configs")
    op.drop_table("alerts")
    op.drop_table("check_results")
    op.drop_table("schema_snapshots")
    op.drop_table("monitored_tables")
    op.drop_table("connections")
    op.drop_table("organizations")
    op.drop_table("users")
```

---

## 6. API Design (Key Endpoints)

RESTful API built with FastAPI. All endpoints require authentication via API key or session token.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/connections` | Create a new warehouse connection |
| POST | `/api/v1/connections/{id}/test` | Test connection credentials |
| GET | `/api/v1/connections/{id}/tables` | List available tables in a connection |
| POST | `/api/v1/tables/monitor` | Add tables to monitoring |
| GET | `/api/v1/tables/{id}/health` | Get table health summary (schema, counts, nulls, cardinality) |
| GET | `/api/v1/alerts` | List alerts (filterable by status, type, table) |
| PATCH | `/api/v1/alerts/{id}` | Update alert status (acknowledge, resolve, snooze) |
| GET | `/api/v1/tables/{id}/schema/history` | Get schema change history for a table |
| PUT | `/api/v1/notifications/config` | Update notification preferences |
| GET | `/api/v1/billing/usage` | Get current usage vs. plan limits |

### Example: FastAPI Router Skeleton

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from typing import Optional

router = APIRouter(prefix="/api/v1", tags=["connections"])


@router.post("/connections")
async def create_connection(payload: ConnectionCreate, user=Depends(get_current_user)):
    """Create a new warehouse connection."""
    ...


@router.post("/connections/{connection_id}/test")
async def test_connection(connection_id: UUID, user=Depends(get_current_user)):
    """Test connection credentials and return status."""
    ...


@router.get("/connections/{connection_id}/tables")
async def list_tables(connection_id: UUID, user=Depends(get_current_user)):
    """List available tables from the connected warehouse."""
    ...


@router.post("/tables/monitor")
async def add_monitored_tables(payload: MonitorTablesRequest, user=Depends(get_current_user)):
    """Add tables to monitoring."""
    ...


@router.get("/tables/{table_id}/health")
async def get_table_health(table_id: UUID, user=Depends(get_current_user)):
    """Get health summary: latest schema, row count, null rates, cardinality."""
    ...


@router.get("/alerts")
async def list_alerts(
    status: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    table_id: Optional[UUID] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    user=Depends(get_current_user),
):
    """List alerts with filtering and pagination."""
    ...


@router.patch("/alerts/{alert_id}")
async def update_alert(alert_id: UUID, payload: AlertUpdate, user=Depends(get_current_user)):
    """Acknowledge, resolve, or snooze an alert."""
    ...
```

---

## 7. Business Model & Pricing

### Pricing Tiers

| Feature | Free | Pro ($99/mo) | Team ($299/mo) |
|---|---|---|---|
| Data Sources | 1 | 3 | 10 |
| Monitored Tables | 5 | Unlimited | Unlimited |
| Check Frequency | Daily | Hourly | Every 15 min |
| Alert History | 7 days | 90 days | 1 year |
| Slack Notifications | ✓ | ✓ | ✓ |
| Email Notifications | — | ✓ | ✓ |
| Custom Alert Thresholds | — | ✓ | ✓ |
| Team Members | 1 | 3 | 15 |
| API Access | — | ✓ | ✓ |
| Custom Webhooks | — | — | ✓ |
| Priority Support | — | Email | Slack + Email |

### Revenue Projections (Year 1)

| Metric | Month 3 | Month 6 | Month 9 | Month 12 |
|---|---|---|---|---|
| Free Users | 50 | 200 | 500 | 1,000 |
| Pro ($99) | 5 | 25 | 60 | 100 |
| Team ($299) | 0 | 5 | 15 | 30 |
| MRR | $495 | $3,970 | $10,425 | $18,870 |

**Target:** $18K+ MRR by end of Year 1, validating product-market fit and justifying full-time transition.

### Unit Economics

- Infrastructure cost per customer: ~$2–$5/mo (mostly warehouse query costs passed through)
- Target gross margin: 85%+
- CAC target: < $200 (content marketing, community, Product Hunt)
- LTV target: > $2,000 (20+ month average retention)

---

## 8. Go-to-Market Strategy

### Launch Channels

1. Product Hunt launch (target top 5 of the day)
2. Hacker News Show HN post with technical deep-dive
3. Data engineering subreddits (r/dataengineering, r/analytics)
4. dbt Community Slack and Locally Optimistic Slack
5. LinkedIn content targeting data team leads at Series A–B companies

### Content Strategy

- Blog series: "Data Quality Horror Stories" — real examples of what goes wrong without monitoring
- Open-source companion: Publish the anomaly detection engine as a standalone Python package
- Comparison pages: PipeCanary vs. Monte Carlo, Great Expectations, Soda (emphasizing cost/simplicity)
- Weekly data engineering newsletter with tips (builds email list for launch)

### Beta Program

Recruit 10–15 beta users from personal network and data engineering communities. Offer lifetime discount (50% off) in exchange for detailed feedback and testimonials. Target: 3–5 case studies before public launch.

### Partnerships

- Snowflake Partner Connect listing (drives discovery from Snowflake's marketplace)
- dbt Cloud integration (post-MVP) for teams already using dbt
- Data engineering bootcamp partnerships (Zach Wilson, DataExpert.io) for awareness

---

## 9. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Enterprise player launches free tier | Medium | High | Move fast; build community moat; focus on simplicity and DX that enterprises can't match |
| Warehouse API breaking changes | Low | Medium | Abstract connector layer; automated integration tests against live warehouses |
| Security breach / credential leak | Low | Critical | Encrypt all creds at rest; use secret managers; SOC 2 compliance; bug bounty program |
| Slow adoption / weak PMF signal | Medium | High | Aggressive free tier; fast iteration based on user feedback; pivot to open-core if needed |
| Side project burnout | Medium | High | Strict scope discipline; 12-week phases; clear go/no-go criteria at each milestone |
| Query cost overruns on customer warehouses | Medium | Medium | Lightweight queries only; cost estimation before onboarding; query budgets per tier |

---

## 10. Success Metrics & Go/No-Go Criteria

### MVP Launch Criteria (Week 12)

- All P0 features functional and tested
- At least 2 warehouse connectors working in production
- 3+ beta customers actively using the product
- Zero critical security vulnerabilities
- End-to-end setup time under 10 minutes

### 3-Month Post-Launch Go/No-Go

| Metric | Continue (Green) | Pivot/Stop (Red) |
|---|---|---|
| Paying Customers | > 10 | < 3 |
| MRR | > $1,000 | < $300 |
| Free-to-Paid Conversion | > 5% | < 1% |
| Weekly Active Users | > 30 | < 10 |
| NPS Score | > 40 | < 10 |

### North Star Metric

**Tables Monitored Per Active Org** — this signals both adoption depth and stickiness. A healthy, engaged customer monitors 15+ tables. If they stop at 2–3, the product isn't delivering enough value.

---

## 11. Tooling & Development Setup

| Category | Tool |
|---|---|
| Language | Python 3.12+ (backend), TypeScript (frontend) |
| API Framework | FastAPI with Pydantic v2 for validation |
| Task Queue | Celery 5.x with Redis broker |
| Database | PostgreSQL 16 with Alembic migrations |
| ORM | SQLAlchemy 2.0 (async) |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Testing | pytest + pytest-asyncio (backend), Vitest + Playwright (frontend) |
| CI/CD | GitHub Actions → Docker build → Deploy |
| Monitoring | Sentry (errors), Posthog (product analytics), UptimeRobot (uptime) |
| Local Dev | Docker Compose (Postgres, Redis, API, worker, frontend) |
| Linting/Formatting | Ruff (Python), ESLint + Prettier (TypeScript) |

---

## 12. Repository Structure

```
pipecanary/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers
│   │   ├── connectors/       # Snowflake, BigQuery, Databricks
│   │   ├── monitoring/       # Schema, row count, null rate, cardinality engines
│   │   ├── anomaly/          # Statistical detection logic
│   │   ├── notifications/    # Slack, email dispatchers
│   │   ├── billing/          # Stripe integration
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   └── tasks/            # Celery task definitions
│   ├── migrations/           # Alembic migrations
│   ├── tests/                # pytest test suite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/            # Route-level pages
│   │   ├── hooks/            # Custom React hooks
│   │   └── api/              # API client layer
│   └── package.json
├── infra/
│   ├── docker-compose.yml    # Local dev environment
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   └── terraform/            # AWS infrastructure (optional)
├── docs/                     # Product and API documentation
└── README.md
```

---

## 13. Immediate Next Steps

Complete these actions this week to kick off Phase 1:

1. Initialize the monorepo with backend (FastAPI) and frontend (React + Vite) scaffolding
2. Set up Docker Compose with PostgreSQL, Redis, and the API server
3. Design and run initial Alembic migrations for users, connections, and monitored_tables
4. Implement the Snowflake connector with `test_connection()` and `get_schema()`
5. Write the first schema snapshot and diff logic
6. Send your first Slack alert from a detected schema change
7. Register domain name and set up GitHub repo with CI pipeline

Once these are done, you'll have a working end-to-end loop: **connect warehouse → detect change → send alert**. Everything else builds on top of that core loop.
