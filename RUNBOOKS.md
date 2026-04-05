# Runbooks

This is the operator index for common tasks during demos and testing.

## Start The App Stack

See [DEPLOYMENT.md](DEPLOYMENT.md).

## Start Monitoring

See [MONITORING.md](MONITORING.md).

## Health Triage

1. Check `/health`
2. Check `/ready`
3. Check `docker compose ps`
4. Check app logs
5. Check Postgres and Redis status

If an alert is firing, continue with [ALERT_RUNBOOK.md](ALERT_RUNBOOK.md).

## Recover A Single App Instance

```bash
docker compose restart web
docker compose restart web2
```

Verify:

```bash
curl http://localhost:5000/health
for i in $(seq 1 5); do curl -s -I http://localhost:5000/health | grep -E 'X-Upstream-Server|X-App-Instance'; done
```

## Recover PostgreSQL

```bash
docker compose start postgres
curl http://localhost:5000/ready
```

If readiness does not recover, inspect Postgres logs before restarting the app layer.

## Demo Cache Behavior

See [SCALING.md](SCALING.md).

## Roll Back A Bad Deploy

See [ROLLBACK.md](ROLLBACK.md).
