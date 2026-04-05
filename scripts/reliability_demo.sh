#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:5000}"

echo "== Reliability smoke =="
echo

echo "-- /health"
curl -sS "${BASE_URL}/health"
echo
echo

echo "-- /ready"
curl -sS "${BASE_URL}/ready"
echo
echo

echo "-- bad JSON shape"
curl -sS -X POST "${BASE_URL}/api/urls" \
  -H 'Content-Type: application/json' \
  -d '["not-an-object"]'
echo
echo

echo "-- wrong field type"
curl -sS -X POST "${BASE_URL}/api/urls" \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"abc","original_url":"https://example.com"}'
echo
echo

echo "-- wrong method"
curl -sS -X POST "${BASE_URL}/health"
echo
echo

cat <<'EOF'
Next manual reliability proofs:

1. Container restart proof
   docker compose kill web
   docker compose ps
   docker inspect -f '{{ .RestartCount }}' "$(docker compose ps -q web)"

2. Readiness degradation proof
   docker compose stop postgres
   curl http://localhost:5000/health
   curl http://localhost:5000/ready
   docker compose start postgres

3. Blocked CI proof
   Push a branch with a deliberately failing test, open a PR, and capture the blocked merge UI.
EOF
