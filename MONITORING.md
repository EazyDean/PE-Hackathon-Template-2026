# Monitoring Guide

The app now exposes Prometheus-compatible metrics at `GET /metrics` and emits structured JSON logs for every request.

## What is included

- Prometheus scrape config and alert rules
- Grafana provisioning with a small starter dashboard
- Alertmanager with a demo-friendly default receiver
- Structured JSON logs with request IDs and latency

## Start the monitoring stack

Start the app stack first:

```bash
docker compose up -d --build
```

Then start monitoring on top:

```bash
docker compose -f compose.yaml -f compose.monitoring.yaml --profile monitoring up -d
docker compose -f compose.yaml -f compose.monitoring.yaml --profile monitoring ps
```

## Endpoints and UIs

- App metrics: `http://localhost:5000/metrics`
- Prometheus: `http://localhost:9090`
- Alertmanager: `http://localhost:9093`
- Grafana: `http://localhost:3000`
  - Username: `admin`
  - Password: `admin`

## What to look at in Grafana

The starter dashboard focuses on the four signals that are easiest to explain in a short demo:

- Traffic rate
- 5xx error rate
- p95 latency
- saturation signals via in-flight requests and memory

## Example alert demo

### Trigger a service-down alert

```bash
docker compose stop web2
```

Wait about 30-60 seconds, then check:

- Prometheus Alerts page
- Alertmanager UI
- `docker compose ps`

### Trigger a high-error-rate alert

Stop Postgres and drive traffic to a DB-backed endpoint:

```bash
docker compose stop postgres
for i in $(seq 1 80); do curl -s -o /dev/null -w '%{http_code}\n' http://localhost:5000/api/users; done
```

Wait about 60-90 seconds, then check Prometheus and Alertmanager again. Bring Postgres back when done:

```bash
docker compose start postgres
```

## Structured logs

Tail one app instance:

```bash
docker compose logs -f web
```

The logs are JSON and include:

- timestamp
- level
- message
- request ID
- method and path
- status code
- latency
- app instance name

Those fields make it easy to connect a spike in Grafana with a concrete failing request in the container logs.

## Related Docs

- [ALERT_RUNBOOK.md](ALERT_RUNBOOK.md)
- [RUNBOOKS.md](RUNBOOKS.md)
- [QUEST_EVIDENCE_CHECKLIST.md](QUEST_EVIDENCE_CHECKLIST.md)
