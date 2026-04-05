# Decision Log

This file records the major technical choices that shape the project.

| Decision | Why | Tradeoff |
| --- | --- | --- |
| Keep Flask + Peewee + PostgreSQL | Matches the hackathon template and keeps the stack simple to explain | Less batteries-included than larger frameworks |
| Model the system as `User`, `ShortUrl`, and `UrlEvent` | Directly matches the seed CSVs and test expectations | Event data is audit-oriented, not full event sourcing |
| Keep core API unauthenticated | Hidden tests and hackathon flows expect a simple public contract | Not appropriate for a production internet-facing service without more controls |
| Use soft delete via `is_active` | Preserves history and matches seeded lifecycle events | Requires redirect logic to explicitly handle inactive links |
| Treat PostgreSQL as source of truth and Redis as fail-open cache | Lets us show caching benefits without risking data integrity | Cache invalidation still needs careful handling |
| Put demo and observability routes under `/internal` and `/metrics` | Adds operations features without changing public API behavior | Slightly larger surface area to document |
| Use Nginx with two app instances | Easy to explain, easy to demo, enough for the scalability track | Single-host Compose is not a full production HA design |
| Use Prometheus + Grafana + Alertmanager | Recognizable observability stack with strong demo value | More moving parts than a logging-only setup |
| Use structured JSON logs | Good for both humans and tooling, and easy to correlate with request IDs | Slightly noisier than plain text for casual local debugging |
