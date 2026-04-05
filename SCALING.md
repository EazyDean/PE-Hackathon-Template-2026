# Scaling Guide

This repo now includes a simple, demo-friendly scaling stack:

- `nginx` reverse proxy / load balancer
- `web` and `web2` Flask app instances
- `redis` for hot-read caching
- `postgres` as the source of truth

Architecture:

`client -> nginx -> web/web2 -> redis + postgres`

## What gets cached

- `GET /<short_code>`
  This is the hottest path in a URL shortener and the best place to show read-scaling wins.

- `GET /api/urls/<identifier>`
  This uses the same cached URL metadata and exposes an `X-Cache` header for verification.

Cache behavior is observable through:

- `X-Cache: HIT|MISS|BYPASS` response headers
- `X-App-Instance` response headers from the Flask container
- `GET /internal/cache/stats`
- `GET /api/internal/cache/stats`

## Start the stack

```bash
docker compose up -d --build
docker compose ps
curl http://localhost:5000/health
curl http://localhost:5000/ready
curl http://localhost:5000/internal/cache/stats
```

## Verify the load balancer

```bash
for i in $(seq 1 5); do curl -s -I http://localhost:5000/health | grep -E 'X-Upstream-Server|X-App-Instance'; done
```

The `X-Upstream-Server` and `X-App-Instance` headers should show requests being served by both app containers.

## Verify cache behavior manually

```bash
curl -s -X POST http://localhost:5000/api/users \
  -H 'Content-Type: application/json' \
  -d '{"username":"cache-demo","email":"cache-demo@example.com"}'
```

Use the returned `id`:

```bash
curl -s -X POST http://localhost:5000/api/urls \
  -H 'Content-Type: application/json' \
  -d '{"user_id":1,"original_url":"https://example.com/cache-demo","title":"cache-demo"}'
```

Use the returned `short_code`:

```bash
curl -I http://localhost:5000/<short_code>
curl -I http://localhost:5000/<short_code>
curl http://localhost:5000/internal/cache/stats
```

You should see the first request return `X-Cache: MISS` and later requests return `X-Cache: HIT`.

## Load tests with k6

Install k6 first if you do not already have it:

```bash
brew install k6
```

All runs below hit the Nginx endpoint and create their own short URL in `setup()`.

### Bronze-style run: 50 virtual users

```bash
mkdir -p artifacts
k6 run \
  -e BASE_URL=http://localhost:5000 \
  -e TARGET_VUS=50 \
  -e DURATION=60s \
  -e WARM_CACHE=true \
  --summary-export=artifacts/k6-50.json \
  load/redirect_hot_path.js
curl http://localhost:5000/internal/cache/stats
```

### Silver-style run: 200 virtual users

```bash
k6 run \
  -e BASE_URL=http://localhost:5000 \
  -e TARGET_VUS=200 \
  -e DURATION=90s \
  -e WARM_CACHE=true \
  --summary-export=artifacts/k6-200.json \
  load/redirect_hot_path.js
curl http://localhost:5000/internal/cache/stats
```

### Gold-style run: 500 virtual users

```bash
k6 run \
  -e BASE_URL=http://localhost:5000 \
  -e TARGET_VUS=500 \
  -e DURATION=120s \
  -e WARM_CACHE=true \
  --summary-export=artifacts/k6-500.json \
  load/redirect_hot_path.js
curl http://localhost:5000/internal/cache/stats
```

## Compare cache off vs cache on

Run one scenario without Redis caching:

```bash
docker compose down
CACHE_ENABLED=false docker compose up -d --build
k6 run \
  -e BASE_URL=http://localhost:5000 \
  -e TARGET_VUS=200 \
  -e DURATION=90s \
  -e WARM_CACHE=false \
  --summary-export=artifacts/k6-200-no-cache.json \
  load/redirect_hot_path.js
```

Then rerun with caching enabled:

```bash
docker compose down
CACHE_ENABLED=true docker compose up -d --build
k6 run \
  -e BASE_URL=http://localhost:5000 \
  -e TARGET_VUS=200 \
  -e DURATION=90s \
  -e WARM_CACHE=true \
  --summary-export=artifacts/k6-200-cache.json \
  load/redirect_hot_path.js
curl http://localhost:5000/internal/cache/stats
```

The most useful comparison is p95 latency and request throughput for the redirect endpoint.

## Suggested evidence to capture

- `docker compose ps` showing `nginx`, `web`, `web2`, `redis`, and `postgres`
- Repeated `X-Upstream-Server` and `X-App-Instance` responses proving both app instances are active
- First and second redirect responses showing `X-Cache: MISS` then `X-Cache: HIT`
- `GET /internal/cache/stats` after the load test
- k6 summary output for 50, 200, and 500 virtual users
- A filled-in [CAPACITY_PLAN_TEMPLATE.md](CAPACITY_PLAN_TEMPLATE.md)
- A filled-in [BOTTLENECK_REPORT_TEMPLATE.md](BOTTLENECK_REPORT_TEMPLATE.md)
- A checked-off [QUEST_EVIDENCE_CHECKLIST.md](QUEST_EVIDENCE_CHECKLIST.md)
