# Failure Modes

This document is the judge-facing reliability guide for how the service should fail, what proof to capture, and which quest tier each proof supports.

## Reliability Tier Map

| Tier | Reliability evidence this repo supports |
| --- | --- |
| Bronze | `GET /health` returns `200`, bad input returns clean JSON errors, and the automated test suite catches regressions |
| Silver | CI fails on broken tests, CI also fails if coverage drops below 70%, and Docker restart behavior can be demonstrated with restart counts |
| Gold | Bronze and Silver evidence plus documented failure modes, readiness-vs-liveness proof, rollback guidance, and a repeatable demo script/checklist |

## Health Semantics

| Endpoint | Meaning | Expected response |
| --- | --- | --- |
| `/health` | Process liveness only | `200 {"status":"ok"}` |
| `/ready` | Database readiness | `200 {"status":"ok","database":"ok"}` or `503 {"status":"degraded","database":"unavailable"}` |
| `/metrics` | Metrics exposure for monitoring | `200 text/plain` |

Reliability demo note:

- `/health` should stay healthy even when PostgreSQL is unavailable.
- `/ready` should degrade when PostgreSQL is unavailable.

## Request-Level Failures

| Failure mode | Expected response | Why this matters | Proof |
| --- | --- | --- | --- |
| Malformed JSON | `400` JSON with `invalid_json` | Prevents stack traces and parser crashes | send a broken JSON body |
| JSON string, array, or `null` body | `400` JSON with `invalid_json` | Hidden tests often probe non-object bodies | send `"x"`, `[]`, or `null` |
| Missing required fields | `400` JSON with `validation_error` | Required contract stays deterministic | omit `user_id` or `original_url` |
| Wrong field types | `400` JSON with `validation_error` | Prevents silent coercion bugs | send string `user_id` or string `is_active` |
| Unknown user or URL reference | `404` JSON with `not_found` | Foreign key lookups fail politely | query or post with fake IDs |
| Duplicate manual short code | `409` JSON with `conflict` | Confirms uniqueness is enforced | create the same manual `short_code` twice |
| Inactive short link | `410` JSON with `inactive` | Confirms soft-delete behavior | deactivate a link and open it |
| Wrong route / wrong method | `404` or `405` JSON | Confirms no HTML fallback leaks through | hit a missing route or bad method |

## Service-Level Failures

| Failure mode | Expected response | Detection | Recovery path |
| --- | --- | --- | --- |
| PostgreSQL unavailable | `/ready` returns `503`; DB-backed routes fail with JSON | `/ready`, logs, CI tests, monitoring | restore Postgres, then recheck readiness |
| Redis unavailable | cache bypass, service still works from Postgres | `X-Cache: BYPASS`, cache stats | restore Redis; no data repair needed |
| Unexpected app exception | `500` JSON | logs and tests | fix route or roll back |
| Broken change in PR | CI fails | GitHub Actions | fix tests/coverage, then rerun |
| Crashed app container | container restarts automatically | `docker compose ps`, restart count | restart policy should resurrect it |

## Exact Demo Commands

### Bronze: health + graceful bad input

```bash
curl http://localhost:5000/health
curl http://localhost:5000/ready

curl -s -X POST http://localhost:5000/api/urls \
  -H 'Content-Type: application/json' \
  -d '["not-an-object"]'

curl -s -X POST http://localhost:5000/api/urls \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"abc","original_url":"https://example.com"}'
```

### Silver: blocked CI + container resurrection

Blocked CI proof:

1. Enable branch protection on `main`
2. Require the `tests` status check
3. Push a branch with a broken test or failing assertion
4. Open a PR and capture the blocked merge UI

Branch-protection note:

- The workflow file makes the check fail.
- GitHub branch protection is what turns that failing check into a blocked merge.

Container resurrection proof:

```bash
docker compose up -d --build
docker compose kill web
docker compose ps
docker inspect -f '{{ .RestartCount }}' "$(docker compose ps -q web)"
curl http://localhost:5000/health
```

### Gold: liveness vs readiness during outage

```bash
docker compose stop postgres
curl http://localhost:5000/health
curl http://localhost:5000/ready
docker compose start postgres
curl http://localhost:5000/ready
```

## Proof Artifacts To Capture

### Bronze

- terminal or screenshot showing `/health` returns `200`
- screenshot or terminal capture of a `400` JSON error body
- screenshot or terminal capture of a passing pytest run

### Silver

- screenshot of GitHub PR page showing failed `tests` check and blocked merge
- screenshot or terminal capture of `docker inspect ... RestartCount`
- screenshot or terminal capture of `docker compose ps` after killing `web`

### Gold

- screenshot showing `/health` still `200` while `/ready` is `503`
- screenshot of [ROLLBACK.md](ROLLBACK.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md), and this document available in the repo
- screenshot of the GitHub Actions run summary showing coverage and the 70% gate

## Fastest Commands For Judges

Use the helper script for the non-destructive part of the reliability demo:

```bash
./scripts/reliability_demo.sh
```

Then run the destructive proofs manually:

```bash
docker compose kill web
docker compose stop postgres
```

## Related Docs

- [README.md](README.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [ROLLBACK.md](ROLLBACK.md)
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- [QUEST_EVIDENCE_CHECKLIST.md](QUEST_EVIDENCE_CHECKLIST.md)
