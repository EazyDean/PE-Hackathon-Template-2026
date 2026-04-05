# Troubleshooting

## Quick Triage Table

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| `/health` is `200` but `/ready` is `503` | PostgreSQL is unavailable | Check `docker compose ps`, restart `postgres`, inspect DB logs |
| Requests are slower but still succeed | Redis is unavailable or bypassed | Check `/internal/cache/stats` and Redis container status |
| `pytest` skips many integration tests | PostgreSQL is not reachable locally | Start Postgres or use Docker Compose before rerunning |
| `409 conflict` on create | Manual short code or email already exists | Retry with a different short code or email |
| `400 invalid_json` | Request body is malformed or not an object | Send a valid JSON object with `Content-Type: application/json` |
| `410 inactive` on redirect | Link was soft-deleted or deactivated | Re-enable the URL via `PATCH` or create a new one |
| Grafana shows no data | Monitoring stack is not running or Prometheus cannot scrape targets | Start the monitoring profile and check Prometheus Targets |
| Port `5000` or `5432` is busy | Another local service is already bound there | Stop the other service or remap ports |

## Common Commands

Check app stack:

```bash
docker compose ps
docker compose logs --tail=100 web
docker compose logs --tail=100 web2
```

Check monitoring stack:

```bash
docker compose -f compose.yaml -f compose.monitoring.yaml --profile monitoring ps
```

Check health:

```bash
curl http://localhost:5000/health
curl http://localhost:5000/ready
curl http://localhost:5000/metrics
curl http://localhost:5000/internal/cache/stats
```

## Seed Data Issues

If you want to reseed from scratch:

```bash
uv run python -m app.seed.loader
```

If you want startup-time reseeding, set:

```env
AUTO_LOAD_SEED_DATA=true
RESET_DATABASE_ON_STARTUP=true
```

Use that carefully, because it rebuilds the seeded tables.
