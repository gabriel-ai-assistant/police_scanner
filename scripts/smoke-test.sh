#!/usr/bin/env bash
# Lightweight smoke test for dev deployments
set -euo pipefail

HOST="${1:?Usage: smoke-test.sh <host>}"
BASE="http://${HOST}"
PASS=0; FAIL=0

check() {
  local name="$1" url="$2" expect="${3:-200}"
  local code
  code=$(curl -sf -o /dev/null -w '%{http_code}' --max-time 10 "$url" 2>/dev/null || echo "000")
  if [[ "$code" == "$expect" ]]; then
    echo "✅ PASS: $name (HTTP $code)"
    ((PASS++))
  else
    echo "❌ FAIL: $name (expected $expect, got $code)"
    ((FAIL++))
  fi
}

echo "=== Smoke Test: $HOST ==="
echo ""

# Retry health endpoint up to 5 times (services may still be starting)
for i in {1..5}; do
  code=$(curl -sf -o /dev/null -w '%{http_code}' --max-time 10 "${BASE}:8000/api/health" 2>/dev/null || echo "000")
  [[ "$code" == "200" ]] && break
  echo "⏳ Waiting for API health... (attempt $i/5)"
  sleep 10
done

check "API Health"    "${BASE}:8000/api/health"
check "Frontend"      "${BASE}:3000"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] || exit 1
