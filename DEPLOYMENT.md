# Deployment Guide

This repo is designed for a simple, explainable hackathon deployment on one machine with Docker Compose.

## Deployment Options

| Option | Best for |
| --- | --- |
| Local `uv run run.py` | development and route debugging |
| `docker compose up -d --build` | app demo with Nginx, 2 app instances, Redis, PostgreSQL |
| `docker compose -f compose.yaml -f compose.monitoring.yaml --profile monitoring up -d` | app demo plus Prometheus, Grafana, and Alertmanager |

## Pre-Deploy Checklist

- `.env` values are correct for the target machine
- `RESET_DATABASE_ON_STARTUP` is `false`
- `DATABASE_*` and `REDIS_URL` point to the intended services
- tests pass locally or in CI
- any seed-loading step has been done intentionally

## Local Deployment

```bash
uv sync
cp .env.example .env
createdb hackathon_db
uv run python -m app.seed.loader
uv run run.py
```

## Docker Deployment

```bash
docker compose up -d --build
docker compose ps
```

Smoke test:

```bash
curl http://localhost:5000/health
curl http://localhost:5000/ready
curl http://localhost:5000/api/users
```

## Monitoring Deployment

```bash
docker compose -f compose.yaml -f compose.monitoring.yaml --profile monitoring up -d
```

UI endpoints:

- `http://localhost:9090` Prometheus
- `http://localhost:9093` Alertmanager
- `http://localhost:3000` Grafana

## Post-Deploy Validation

Run these after every deploy:

```bash
curl http://localhost:5000/health
curl http://localhost:5000/ready
curl http://localhost:5000/metrics
curl http://localhost:5000/internal/cache/stats
```

Optional stronger smoke test:

1. Create a user
2. Create a short URL
3. Open the short URL
4. Confirm the redirect succeeds and an event is logged

## Deployment Assumptions

- Single-host deployment is acceptable for the hackathon
- Docker restart policy is enough for demo-grade resurrection
- PostgreSQL remains the only source of truth
