# Alert Runbook

## Alert: `ShortenerInstanceDown`

### What it means

Prometheus cannot scrape one of the app instances for at least 30 seconds.

### First checks

1. Run `docker compose ps`
2. Check the stopped or unhealthy container with `docker compose logs --tail=100 web` or `docker compose logs --tail=100 web2`
3. Confirm whether the issue is only one app instance or a broader dependency problem

### Likely causes

- container crash or bad boot
- failed dependency startup order
- bad config pushed to one instance
- resource starvation on the host

### Immediate actions

1. Restart the affected instance with `docker compose restart web` or `docker compose restart web2`
2. If both instances are unhealthy, inspect `postgres` and `redis`
3. Verify recovery with:
   - `curl http://localhost:5000/health`
   - `curl http://localhost:5000/ready`
   - Prometheus Targets page

### Evidence to capture

- failing alert in Prometheus or Alertmanager
- `docker compose ps`
- recent container logs
- recovery after restart

## Alert: `ShortenerHighErrorRate`

### What it means

More than 5% of recent requests are returning 5xx responses for at least one minute.

### First checks

1. Open Grafana and inspect latency, traffic, and error-rate panels
2. Tail logs from both app instances:
   - `docker compose logs -f web`
   - `docker compose logs -f web2`
3. Check dependent services:
   - `docker compose ps`
   - `curl http://localhost:5000/ready`

### Likely causes

- PostgreSQL unavailable or overloaded
- Redis unavailable causing slower fallback behavior
- bad deploy introducing unhandled exceptions
- malformed traffic exercising an unprotected edge case

### Immediate actions

1. Identify whether errors are concentrated on one route or widespread
2. If the database is down, recover Postgres first
3. If only one app instance is noisy, compare `X-App-Instance` responses and restart that instance
4. Confirm recovery by watching:
   - request success rate improve
   - 5xx error rate drop in Grafana
   - alert resolve in Alertmanager

### Root-cause workflow

1. Use Grafana to determine when the incident started and whether latency rose before errors
2. Match the time window in structured logs using request IDs and status codes
3. Verify dependency health with `/ready` and container status
4. Summarize the cause, mitigation, and whether the issue was app-local, DB-related, or infrastructure-related

### Evidence to capture

- alert firing screen
- Grafana panels around the incident window
- structured log lines showing failing requests
- the recovery point when the alert resolves

## Related Docs

- [MONITORING.md](MONITORING.md)
- [ROLLBACK.md](ROLLBACK.md)
- [QUEST_EVIDENCE_CHECKLIST.md](QUEST_EVIDENCE_CHECKLIST.md)
