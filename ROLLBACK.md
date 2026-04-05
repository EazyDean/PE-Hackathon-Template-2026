# Rollback Guide

This project is optimized for simple, predictable rollback in a hackathon setting.

## When To Roll Back

Roll back if:

- `/ready` stays `503` after a deploy
- the public API starts returning unexpected `5xx` responses
- alert noise increases immediately after a change
- the demo environment becomes unstable and the fastest safe fix is a known-good version

## Fast Docker Rollback

1. Identify the last known-good commit or tag.
2. Switch the repo back to it.
3. Rebuild and restart the stack.

```bash
git log --oneline
git checkout <known-good-commit>
docker compose down
docker compose up -d --build
```

If monitoring is enabled:

```bash
docker compose -f compose.yaml -f compose.monitoring.yaml --profile monitoring up -d
```

## Local Rollback

```bash
git checkout <known-good-commit>
uv sync
uv run run.py
```

## Data Safety Notes

- Do not use `RESET_DATABASE_ON_STARTUP=true` during rollback unless you intentionally want to wipe and reload seed data.
- Redis can be discarded during rollback because it is only a cache.
- PostgreSQL should be preserved unless the rollback is specifically about restoring seeded demo data.

## Rollback Verification

After rollback, confirm:

```bash
curl http://localhost:5000/health
curl http://localhost:5000/ready
curl http://localhost:5000/api/users
curl http://localhost:5000/metrics
```

Then confirm the alerting and dashboard view recover if monitoring is enabled.
