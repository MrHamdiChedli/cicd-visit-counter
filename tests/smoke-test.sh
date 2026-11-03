#!/usr/bin/env bash
# Checks the running Compose stack: load balancing, isolation, failover and data persistence.
# Run it where Docker runs (inside the VM: vagrant ssh -c "cd /vagrant && bash tests/smoke-test.sh").
set -euo pipefail
cd "$(dirname "$0")/.."

LB_URL="${LB_URL:-http://localhost:8080}"
fail() { echo "FAIL: $1"; exit 1; }

hits() {
  for _ in $(seq 1 "$1"); do
    curl -fsS --max-time 5 "$LB_URL/" || fail "request to $LB_URL/ failed"
    echo
  done
}
served_by() { grep -o '"served_by":"[^"]*"' | sort -u | wc -l | tr -d ' '; }
visits() { hits 1 | grep -o '"visits":[0-9]*' | cut -d: -f2; }

echo "1. Health check through the load balancer"
curl -fsS --max-time 5 "$LB_URL/healthz" > /dev/null || fail "/healthz is not healthy"

echo "2. Traffic reaches both app replicas"
[ "$(hits 10 | served_by)" = "2" ] || fail "expected 2 replicas to answer"

echo "3. The counter is shared through the database"
first=$(visits); second=$(visits)
[ "$second" -gt "$first" ] || fail "counter did not increase ($first then $second)"

echo "4. Only the load balancer is published, and it can't reach the database"
if curl -fsS --max-time 3 http://localhost:8000/ > /dev/null 2>&1; then
  fail "the app is reachable without going through the load balancer"
fi
if docker compose exec -T lb nc -z -w 2 db 5432 > /dev/null 2>&1; then
  fail "the load balancer can reach the database"
fi

echo "5. The app runs as a non-root user on a read-only filesystem"
[ "$(docker compose exec -T app id -u)" != "0" ] || fail "the app runs as root"
[ "$(docker inspect visit-counter-app-1 --format '{{.HostConfig.ReadonlyRootfs}}')" = "true" ] \
  || fail "the app filesystem is writable"

echo "6. Failover: stop one replica, every request must still succeed"
docker stop visit-counter-app-1 > /dev/null
trap 'docker start visit-counter-app-1 > /dev/null' EXIT
[ "$(hits 10 | served_by)" = "1" ] || fail "expected only the remaining replica to answer"

echo "7. Data survives recreating the database container"
before=$(visits)
docker compose up --detach --force-recreate --wait db > /dev/null 2>&1
after=$(visits)
[ "$after" -gt "$before" ] || fail "the counter was reset ($before then $after)"

echo "PASS: all checks succeeded"
