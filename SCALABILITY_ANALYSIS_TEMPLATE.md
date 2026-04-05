# Scalability Analysis Template

This file is the detailed companion to [BOTTLENECK_REPORT_TEMPLATE.md](BOTTLENECK_REPORT_TEMPLATE.md). Use it when you want a fuller write-up after load testing.

## Scenario

- Date:
- Commit / branch:
- Environment:
- Cache enabled:
- Test profile:
  - `50 users`
  - `200 users`
  - `500 users`
- Duration:

## Topline Results

- Requests per second:
- Average latency:
- p50 latency:
- p95 latency:
- p99 latency:
- Error rate:

## Cache Observations

- `X-Cache` behavior observed:
- `/internal/cache/stats` before run:
- `/internal/cache/stats` after run:
- Hit ratio:

## Infrastructure Observations

- Nginx CPU / memory:
- `web` CPU / memory:
- `web2` CPU / memory:
- Redis CPU / memory:
- PostgreSQL CPU / memory:

## Bottleneck Analysis

- First bottleneck seen:
- Evidence:
- Why this happened:

## Comparison: Cache Off vs Cache On

- p95 delta:
- Throughput delta:
- Error-rate delta:
- Notes:

## Next Optimization

- What I would change next:
- Expected impact:
- Risk / tradeoff:
