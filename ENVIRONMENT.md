# Environment Variables

This project reads configuration from `.env` and environment variables. Start from [.env.example](.env.example).

## Runtime Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `FLASK_DEBUG` | `true` locally | Enables Flask debug mode for local development |
| `APP_HOST` | `127.0.0.1` | Bind address for `run.py` |
| `APP_PORT` | `5000` | Port for the Flask app |
| `APP_INSTANCE_NAME` | hostname | Friendly instance label used in response headers and logs |
| `LOG_LEVEL` | `INFO` | Structured application log level |
| `DATABASE_NAME` | `hackathon_db` | PostgreSQL database name |
| `DATABASE_HOST` | `localhost` | PostgreSQL host |
| `DATABASE_PORT` | `5432` | PostgreSQL port |
| `DATABASE_USER` | `postgres` | PostgreSQL username |
| `DATABASE_PASSWORD` | `postgres` | PostgreSQL password |
| `SEED_DIRECTORY` | `app/seed` | Location of `users.csv`, `urls.csv`, and `events.csv` |
| `AUTO_CREATE_TABLES` | `true` | Creates tables on app startup |
| `AUTO_LOAD_SEED_DATA` | `false` | Loads seed CSVs on app startup |
| `RESET_DATABASE_ON_STARTUP` | `false` | Drops and reloads seeded tables on startup |

## Cache Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `CACHE_ENABLED` | `true` | Turns Redis cache on or off |
| `CACHE_TTL_SECONDS` | `300` | TTL for cached URL snapshots |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `REDIS_TIMEOUT_SECONDS` | `0.5` | Redis connect and socket timeout |

## Test Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `TEST_DATABASE_NAME` | `hackathon_test_db` | Pytest integration database |
| `TEST_DATABASE_ADMIN` | `postgres` | Admin DB used to create the test DB if needed |

## Recommended Profiles

### Local development

```env
FLASK_DEBUG=true
APP_HOST=127.0.0.1
APP_PORT=5000
DATABASE_HOST=localhost
CACHE_ENABLED=true
```

### Docker Compose app stack

```env
FLASK_DEBUG=false
APP_HOST=0.0.0.0
APP_PORT=5000
DATABASE_HOST=postgres
REDIS_URL=redis://redis:6379/0
```

### Safe demo note

Avoid enabling `RESET_DATABASE_ON_STARTUP=true` on any environment where you want to keep existing data.
