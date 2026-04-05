# URL Shortener Backend

Hackathon-ready URL shortener backend built with Flask, Peewee, PostgreSQL, Redis, Nginx, and Prometheus-friendly observability.

The core public API stays unauthenticated and JSON-first. Reliability, scalability, and incident-response features are layered around that contract instead of changing it.

Assumptions:

- You have `uv` installed for local development.
- You have either local PostgreSQL or Docker Desktop available.
- Seed CSVs live in `app/seed/`.

## Quick Start From Scratch

### Local development

```bash
git clone <repo-url>
cd PE-Hackathon-Template-2026
uv sync
cp .env.example .env
createdb hackathon_db
uv run python -m app.seed.loader
uv run run.py
```

Smoke test:

```bash
curl http://localhost:5000/health
curl http://localhost:5000/ready
curl http://localhost:5000/metrics
.venv/bin/pytest -q
```

### Docker demo stack

```bash
docker compose up -d --build
docker compose ps
curl http://localhost:5000/health
curl http://localhost:5000/ready
```

### Monitoring overlay

```bash
docker compose -f compose.yaml -f compose.monitoring.yaml --profile monitoring up -d
curl http://localhost:5000/metrics
```

## Architecture

```text
Clients / curl / k6
        |
        v
   Nginx reverse proxy
        |
   +----+----+
   |         |
   v         v
 web       web2         Flask + Peewee app instances
   | \       / |
   |  \     /  |
   |   \   /   |
   v    v v    v
 Redis  PostgreSQL       cache + source of truth

 Prometheus <-- /metrics --> app instances
      |
 Alertmanager
      |
 Grafana
```

## What This Repo Demonstrates

- Public URL-shortener API with create, fetch, redirect, update, delete, and event history
- Deterministic validation and JSON error responses
- Seed loading from CSV snapshots and audit events
- Docker Compose with Nginx, two app instances, Redis, and PostgreSQL
- Structured JSON logs and Prometheus metrics
- Load-test scaffolding, runbooks, rollback steps, and evidence checklists

## Hackathon Evidence Map

| Area | Where to look | What to show a judge |
| --- | --- | --- |
| Reliability | [FAILURE_MODES.md](FAILURE_MODES.md), [DEPLOYMENT.md](DEPLOYMENT.md), [tests](tests), `.github/workflows/ci.yml` | JSON 4xx/5xx handling, `/health` vs `/ready`, CI failing on broken tests, Docker restart behavior |
| Scalability | [SCALING.md](SCALING.md), [compose.yaml](compose.yaml), [load/redirect_hot_path.js](load/redirect_hot_path.js), [CAPACITY_PLAN_TEMPLATE.md](CAPACITY_PLAN_TEMPLATE.md) | Two app instances behind Nginx, Redis cache hits, k6 summaries for 50/200/500 users |
| Incident Response | [MONITORING.md](MONITORING.md), [ALERT_RUNBOOK.md](ALERT_RUNBOOK.md), [compose.monitoring.yaml](compose.monitoring.yaml), [monitoring](monitoring) | `/metrics`, Prometheus alerts, Grafana dashboard, structured logs, alert triage story |
| Documentation | [API.md](API.md), [ENVIRONMENT.md](ENVIRONMENT.md), [ROLLBACK.md](ROLLBACK.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md), [QUEST_EVIDENCE_CHECKLIST.md](QUEST_EVIDENCE_CHECKLIST.md) | Setup from scratch, endpoint docs, env vars, rollback guide, troubleshooting, evidence checklist |

## Documentation Index

| Document | Purpose |
| --- | --- |
| [API.md](API.md) | Endpoint-by-endpoint API contract |
| [ENVIRONMENT.md](ENVIRONMENT.md) | Runtime and test environment variables |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Local, Docker, and monitored deployment flow |
| [ROLLBACK.md](ROLLBACK.md) | Safe rollback procedure for demo deployments |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common issues and quick fixes |
| [DECISION_LOG.md](DECISION_LOG.md) | Why the major technical choices were made |
| [RUNBOOKS.md](RUNBOOKS.md) | Operator task index and response playbooks |
| [FAILURE_MODES.md](FAILURE_MODES.md) | Expected failure behavior and proof artifacts |
| [SCALING.md](SCALING.md) | Load-balancing, caching, and load-test guide |
| [MONITORING.md](MONITORING.md) | Metrics, dashboards, and alert demo steps |
| [ALERT_RUNBOOK.md](ALERT_RUNBOOK.md) | Response guide for alert scenarios |
| [CAPACITY_PLAN_TEMPLATE.md](CAPACITY_PLAN_TEMPLATE.md) | Capacity planning worksheet |
| [BOTTLENECK_REPORT_TEMPLATE.md](BOTTLENECK_REPORT_TEMPLATE.md) | Post-test bottleneck analysis template |
| [QUEST_EVIDENCE_CHECKLIST.md](QUEST_EVIDENCE_CHECKLIST.md) | Submission proof checklist by track |

## Common Commands

| Task | Command |
| --- | --- |
| Install deps | `uv sync` |
| Seed the database | `uv run python -m app.seed.loader` |
| Run the app locally | `uv run run.py` |
| Run tests | `.venv/bin/pytest -q` |
| Start app stack | `docker compose up -d --build` |
| Start monitoring stack | `docker compose -f compose.yaml -f compose.monitoring.yaml --profile monitoring up -d` |
| Run 200-user load test | `k6 run -e BASE_URL=http://localhost:5000 -e TARGET_VUS=200 -e DURATION=90s -e WARM_CACHE=true load/redirect_hot_path.js` |

## Project Structure

```text
app/
  __init__.py            Flask app factory and startup hooks
  database.py            Peewee database wiring
  models/                User, ShortUrl, UrlEvent
  routes/                Public API and redirect handlers
  seed/                  CSV seed data and loader
  cache.py               Redis cache helpers
  observability.py       Structured logging and Prometheus metrics
load/                    k6 load test scripts
monitoring/              Prometheus, Grafana, Alertmanager config
nginx/                   Reverse proxy and load balancer config
tests/                   Unit and integration-style pytest suite
```

## Public API Summary

Core public routes:

- `POST /api/users`
- `GET /api/users`
- `POST /api/urls`
- `GET /api/urls`
- `GET /api/urls/<identifier>`
- `PATCH /api/urls/<identifier>`
- `DELETE /api/urls/<identifier>`
- `GET /api/events`
- `GET /<short_code>`

Full request and response details live in [API.md](API.md).

## Notes For Judges

- The public backend contract remains simple and unauthenticated.
- Extra operational features live under `/internal/*`, `/metrics`, Docker Compose, and the monitoring overlay.
- Redis is a cache, not the source of truth. PostgreSQL remains canonical.
- `/health` and `/ready` intentionally mean different things so liveness and dependency health can be demonstrated separately.
