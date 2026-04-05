# API Reference

The core API is unauthenticated and JSON-first. Most resource routes are available both with and without the `/api` prefix. The redirect route is `GET /<short_code>`.

## Conventions

- Request bodies must be JSON objects.
- Successful writes return the created or updated resource.
- Validation failures return JSON, never HTML stack traces.
- Standard error shape:

```json
{
  "error": "validation_error",
  "message": "'user_id' is required."
}
```

## System Endpoints

| Method | Path | Purpose | Success |
| --- | --- | --- | --- |
| `GET` | `/health` | Process liveness check | `200 {"status":"ok"}` |
| `GET` | `/ready` | PostgreSQL readiness check | `200` or `503` |
| `GET` | `/metrics` | Prometheus metrics exposure | `200 text/plain` |

## User Endpoints

These routes exist as both `/users` and `/api/users`.

| Method | Path | Purpose | Request | Success |
| --- | --- | --- | --- | --- |
| `GET` | `/users` | List users | none | `200 {"count":...,"items":[...]}` |
| `POST` | `/users` | Create a user | `{"username":"...","email":"..."}` | `201` user object |
| `GET` | `/users/<user_id>` | Get one user | path param | `200` user object with `url_count` |
| `GET` | `/users/<user_id>/urls` | List a user's short URLs | path param | `200 {"user":...,"count":...,"items":[...]}` |

## URL Endpoints

These routes exist as both `/urls` and `/api/urls`.

### List and Create

| Method | Path | Purpose | Request | Success |
| --- | --- | --- | --- | --- |
| `GET` | `/urls` | List short URLs | Query: `user_id`, `active`, `is_active` | `200 {"count":...,"items":[...]}` |
| `POST` | `/urls` | Create short URL | `{"user_id":1,"original_url":"https://...","title":"...","short_code":"abc123","is_active":true}` | `201` URL object |

Create notes:

- `user_id` and `original_url` are required.
- `short_code` is optional. If omitted, the server generates one.
- Duplicate manual short codes return `409`.

### Read, Update, Delete

`<identifier>` can be a short code and, when numeric, can also resolve by URL row ID.

| Method | Path | Purpose | Request | Success |
| --- | --- | --- | --- | --- |
| `GET` | `/urls/<identifier>` | Get one short URL | none | `200` URL object plus `event_count` |
| `PATCH` | `/urls/<identifier>` | Update mutable fields | `{"original_url":"...","title":"...","is_active":false}` | `200` updated URL object |
| `DELETE` | `/urls/<identifier>` | Soft-delete by marking inactive | optional `{"reason":"user_requested"}` | `200` URL object with `is_active:false` |
| `GET` | `/urls/<identifier>/events` | List events for one URL | none | `200 {"short_code":"...","count":...,"items":[...]}` |

Update notes:

- Allowed fields are `original_url`, `title`, and `is_active`.
- Unknown fields return `400`.
- Empty patch bodies return `400`.

Delete notes:

- Delete is a soft delete.
- Allowed reasons are `duplicate`, `user_requested`, `expired`, and `policy_cleanup`.

## Event Endpoint

These routes exist as both `/events` and `/api/events`.

| Method | Path | Purpose | Query Filters | Success |
| --- | --- | --- | --- | --- |
| `GET` | `/events` | List audit events | `short_code`, `url_id`, `user_id`, `event_type` | `200 {"count":...,"items":[...]}` |

## Redirect Endpoint

| Method | Path | Purpose | Success |
| --- | --- | --- | --- |
| `GET` | `/<short_code>` | Redirect to the original URL | `302` redirect |

Redirect notes:

- Active links return a `302`.
- Inactive links return `410`.
- Successful redirects create a `visited` event.
- Response headers include `X-Cache` so cache hits and misses are easy to prove.

## Internal Demo Endpoints

These routes exist as both `/internal/cache/stats` and `/api/internal/cache/stats`.

| Method | Path | Purpose | Success |
| --- | --- | --- | --- |
| `GET` | `/internal/cache/stats` | Show cache hit/miss counters | `200` JSON stats |

These endpoints are for demos and operations. They do not change the public backend contract.

## Common Error Cases

| Case | Status | Notes |
| --- | --- | --- |
| Malformed JSON | `400` | Returns `invalid_json` |
| Wrong JSON type | `400` | Arrays and strings are rejected where an object is required |
| Missing field | `400` | Returns `validation_error` |
| Unknown foreign key | `404` | Unknown `user_id` or `url_id` |
| Duplicate short code | `409` | Manual conflicts only |
| Inactive redirect | `410` | No redirect performed |
| DB unavailable | `503` | Readiness and request handlers fail cleanly |
