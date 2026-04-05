# Failure Modes

This document explains how the service is expected to fail and how to prove that behavior during judging.

## Request-Level Failures

| Failure mode | Expected response | Detection | Proof |
| --- | --- | --- | --- |
| Malformed JSON | `400` JSON | API response body | `curl` with broken JSON |
| Wrong JSON shape | `400` JSON | API response body | send a JSON string or array |
| Missing required fields | `400` JSON | API response body | omit `user_id` or `original_url` |
| Bad IDs or unknown references | `400` or `404` JSON | API response body | query missing `user_id` or `url_id` |
| Inactive short link | `410` JSON | API response body | delete a link, then open it |
| Duplicate short code | `409` JSON | API response body | try creating the same manual `short_code` twice |

## Service-Level Failures

| Failure mode | Expected response | Detection | Recovery path |
| --- | --- | --- | --- |
| PostgreSQL unavailable | `503` JSON or `/ready` = `503` | `/ready`, logs, alerts | recover Postgres, then recheck readiness |
| Redis unavailable | cache bypass, app still serves DB-backed reads | `X-Cache: BYPASS`, cache stats | restore Redis; no data repair needed |
| Unexpected app exception | `500` JSON | logs, metrics, alerts | inspect logs, fix route or roll back |
| Unknown route / wrong method | `404` / `405` JSON | API response body | no action needed; this is expected behavior |

## Health Semantics

| Endpoint | Meaning |
| --- | --- |
| `/health` | Process is alive |
| `/ready` | App can reach PostgreSQL |
| `/metrics` | Prometheus can scrape app metrics |

## Demo Scenarios

### Container resurrection

```bash
docker compose up -d --build
docker compose kill web
docker inspect -f '{{ .RestartCount }}' "$(docker compose ps -q web)"
```

### Database outage

```bash
docker compose stop postgres
curl http://localhost:5000/health
curl http://localhost:5000/ready
docker compose start postgres
```

### Bad request handling

```bash
curl -s -X POST http://localhost:5000/api/urls \
  -H 'Content-Type: application/json' \
  -d '["not-an-object"]'
```

## Related Docs

- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- [ROLLBACK.md](ROLLBACK.md)
- [ALERT_RUNBOOK.md](ALERT_RUNBOOK.md)
- [QUEST_EVIDENCE_CHECKLIST.md](QUEST_EVIDENCE_CHECKLIST.md)
