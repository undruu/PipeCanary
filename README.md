# PipeCanary

PipeCanary is a lightweight, affordable data quality observability platform for small teams. It monitors your data warehouse tables for schema drift, row-count anomalies, and freshness issues — then alerts you via Slack before bad data reaches production.

## Architecture

| Component | Tech | Purpose |
|-----------|------|---------|
| **API** | FastAPI + SQLAlchemy (async) | REST endpoints for connections, tables, alerts, notifications |
| **Worker** | Celery + Redis | Scheduled monitoring checks (schema drift, row counts, freshness) |
| **Frontend** | React 18 + TypeScript + Vite + Tailwind CSS | Dashboard, connection management, alert triage |
| **Database** | PostgreSQL 16 | Persistent storage for configs, snapshots, and alerts |
| **Broker** | Redis 7 | Celery task queue and result backend |

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/AFolken/pipecanary.git
cd pipecanary

# 2. Start all services
docker compose -f infra/docker-compose.yml up --build

# 3. Run the database migration (in a separate terminal)
docker compose -f infra/docker-compose.yml exec api alembic upgrade head
```

Once running:

- **Frontend** — http://localhost:5173
- **API docs (Swagger)** — http://localhost:8000/docs
- **Health check** — http://localhost:8000/health

## Running Without Docker

### Backend

```bash
cd backend
cp .env.example .env          # edit connection strings if needed
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Requires a running PostgreSQL and Redis instance. Connection strings are configured via environment variables with the `PIPECANARY_` prefix (see `backend/.env.example`).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` requests to `http://localhost:8000`.

## Project Structure

```
pipecanary/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Pydantic settings (env vars)
│   │   ├── database.py          # SQLAlchemy async engine
│   │   ├── celery_app.py        # Celery config + beat schedule
│   │   ├── api/                 # Route handlers
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── connectors/          # Warehouse connectors (Snowflake)
│   │   ├── anomaly/             # Statistical anomaly detection
│   │   ├── monitoring/          # Schema diff engine
│   │   ├── notifications/       # Slack integration
│   │   └── tasks/               # Celery tasks
│   ├── migrations/              # Alembic migrations
│   ├── tests/                   # pytest suite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Routes
│   │   ├── api/client.ts        # API client
│   │   ├── pages/               # Dashboard, Connections, Alerts
│   │   └── components/          # Layout, shared UI
│   ├── package.json
│   └── vite.config.ts
└── infra/
    ├── docker-compose.yml       # Full-stack dev environment
    ├── Dockerfile.api
    ├── Dockerfile.frontend
    └── Dockerfile.worker
```

## Environment Variables

All backend config uses the `PIPECANARY_` prefix. See `backend/.env.example` for the full list:

| Variable | Default | Description |
|----------|---------|-------------|
| `PIPECANARY_DATABASE_URL` | `postgresql+asyncpg://pipecanary:pipecanary@localhost:5432/pipecanary` | Async DB connection |
| `PIPECANARY_REDIS_URL` | `redis://localhost:6379/0` | Redis broker URL |
| `PIPECANARY_DEBUG` | `false` | Enable debug logging |
| `PIPECANARY_AUTH_SECRET_KEY` | `change-me-in-production` | JWT signing key |
| `PIPECANARY_SLACK_WEBHOOK_URL` | *(empty)* | Slack incoming webhook |
| `PIPECANARY_SNOWFLAKE_ACCOUNT` | *(empty)* | Snowflake account identifier |

## Tests

```bash
cd backend
pip install -r requirements.txt
pytest
```

## Linting

```bash
cd backend
ruff check .
```
