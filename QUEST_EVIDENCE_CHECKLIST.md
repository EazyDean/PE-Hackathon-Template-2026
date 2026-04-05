# Quest Evidence Checklist

Use this checklist when preparing your submission screenshots, recordings, or live demo.

## Reliability

### Bronze

- [ ] Screenshot or terminal capture of `GET /health` returning `200`
- [ ] Screenshot or terminal capture of a graceful JSON `400` response
- [ ] Test run output showing a passing suite

### Silver

- [ ] Screenshot of failing CI check blocking merge
- [ ] Screenshot or terminal capture of `docker inspect ... RestartCount`
- [ ] Screenshot or terminal capture of `docker compose ps` after killing `web`

### Gold

- [ ] Proof that `/health` stays up while `/ready` reflects DB loss
- [ ] Screenshot of the GitHub Actions run summary showing coverage
- [ ] Screenshot or terminal capture showing the 70% coverage gate in CI
- [ ] Screenshot of [FAILURE_MODES.md](FAILURE_MODES.md) in the repo

## Scalability

- [ ] `docker compose ps` showing `nginx`, `web`, `web2`, `redis`, `postgres`
- [ ] `X-Upstream-Server` and `X-App-Instance` responses from both app instances
- [ ] `X-Cache: MISS` then `X-Cache: HIT`
- [ ] k6 summary for 50 users
- [ ] k6 summary for 200 users
- [ ] k6 summary for 500 users
- [ ] Completed [CAPACITY_PLAN_TEMPLATE.md](CAPACITY_PLAN_TEMPLATE.md)
- [ ] Completed [BOTTLENECK_REPORT_TEMPLATE.md](BOTTLENECK_REPORT_TEMPLATE.md)

## Incident Response

- [ ] Screenshot of `/metrics` or Prometheus Targets page
- [ ] Screenshot of Grafana dashboard with traffic, latency, and errors
- [ ] Screenshot of a firing alert in Prometheus or Alertmanager
- [ ] Structured JSON log lines showing request context
- [ ] Completed alert-response walkthrough using [ALERT_RUNBOOK.md](ALERT_RUNBOOK.md)

## Documentation

- [ ] README shows setup from scratch
- [ ] API docs cover all endpoints
- [ ] Environment variables are documented
- [ ] Deployment and rollback guides are present
- [ ] Troubleshooting and runbooks are present
- [ ] Decision log is present
- [ ] Failure modes are documented
- [ ] Hackathon Evidence Map is present in README
