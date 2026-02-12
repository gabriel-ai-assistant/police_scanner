#!/usr/bin/env bash
# Comprehensive staging test gate — must ALL pass before promoting to main
set -uo pipefail

HOST="${1:?Usage: staging-tests.sh <host>}"
BASE="http://${HOST}"
API="${BASE}:8000"
FRONTEND="${BASE}:3000"
PASS=0; FAIL=0; TOTAL=0

pass() { ((PASS++)); ((TOTAL++)); echo "✅ PASS: $1"; }
fail() { ((FAIL++)); ((TOTAL++)); echo "❌ FAIL: $1 — $2"; }

section() { echo ""; echo "━━━ $1 ━━━"; }

# ── Wait for services ──────────────────────────────────────────────
section "Service Readiness"
echo "Waiting for API to be reachable..."
for i in {1..12}; do
  curl -sf --max-time 5 "${API}/api/health" >/dev/null 2>&1 && break
  echo "  ⏳ attempt $i/12..."
  sleep 10
done

# ── API Health ─────────────────────────────────────────────────────
section "API Health & Core Endpoints"

code=$(curl -sf -o /dev/null -w '%{http_code}' --max-time 10 "${API}/api/health" 2>/dev/null || echo "000")
[[ "$code" == "200" ]] && pass "GET /api/health → 200" || fail "GET /api/health" "got $code"

# ── Auth Flow ──────────────────────────────────────────────────────
section "Authentication Flow"

# Try to login (assumes test credentials exist; adapt as needed)
TOKEN=""
LOGIN_RESP=$(curl -sf --max-time 10 -X POST "${API}/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}' 2>/dev/null || echo "")

if echo "$LOGIN_RESP" | grep -q '"token"\|"access_token"\|"jwt"'; then
  TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('token', d.get('access_token', d.get('jwt',''))))" 2>/dev/null || echo "")
  pass "Auth: login returns token"
else
  fail "Auth: login" "no token in response"
fi

# Protected endpoint without auth → 401
code=$(curl -sf -o /dev/null -w '%{http_code}' --max-time 10 "${API}/api/calls" 2>/dev/null || echo "000")
[[ "$code" == "401" || "$code" == "403" ]] && pass "Security: /api/calls without auth → $code" || fail "Security: /api/calls without auth" "expected 401/403, got $code"

# Protected endpoint with auth
if [[ -n "$TOKEN" ]]; then
  AUTH_HEADER="Authorization: Bearer ${TOKEN}"

  for ep in "/api/calls" "/api/playlists" "/api/analytics/hourly-activity" "/api/dashboard/stats"; do
    resp=$(curl -sf --max-time 10 -H "$AUTH_HEADER" "${API}${ep}" 2>/dev/null || echo "")
    code=$(curl -sf -o /dev/null -w '%{http_code}' --max-time 10 -H "$AUTH_HEADER" "${API}${ep}" 2>/dev/null || echo "000")
    if [[ "$code" == "200" ]] && echo "$resp" | python3 -c "import sys,json;json.load(sys.stdin)" 2>/dev/null; then
      pass "GET ${ep} → 200 + valid JSON"
    else
      fail "GET ${ep}" "HTTP $code or invalid JSON"
    fi
  done
else
  for ep in "/api/calls" "/api/playlists" "/api/analytics/hourly-activity" "/api/dashboard/stats"; do
    fail "GET ${ep} (authed)" "skipped — no token"
  done
fi

# ── Security: more protected endpoints ─────────────────────────────
section "Security Checks"

for ep in "/api/playlists" "/api/analytics/hourly-activity" "/api/dashboard/stats"; do
  code=$(curl -sf -o /dev/null -w '%{http_code}' --max-time 10 "${API}${ep}" 2>/dev/null || echo "000")
  [[ "$code" == "401" || "$code" == "403" ]] && pass "No-auth ${ep} → $code" || fail "No-auth ${ep}" "expected 401/403, got $code"
done

# ── Performance ────────────────────────────────────────────────────
section "Performance Baseline"

if [[ -n "$TOKEN" ]]; then
  for ep in "/api/health" "/api/calls" "/api/dashboard/stats"; do
    time_total=$(curl -sf -o /dev/null -w '%{time_total}' --max-time 10 -H "$AUTH_HEADER" "${API}${ep}" 2>/dev/null || echo "99")
    if (( $(echo "$time_total < 2.0" | bc -l) )); then
      pass "Perf: ${ep} responded in ${time_total}s (<2s)"
    else
      fail "Perf: ${ep}" "took ${time_total}s (>2s)"
    fi
  done
else
  time_total=$(curl -sf -o /dev/null -w '%{time_total}' --max-time 10 "${API}/api/health" 2>/dev/null || echo "99")
  if (( $(echo "$time_total < 2.0" | bc -l) )); then
    pass "Perf: /api/health responded in ${time_total}s (<2s)"
  else
    fail "Perf: /api/health" "took ${time_total}s (>2s)"
  fi
fi

# ── Docker Health ──────────────────────────────────────────────────
section "Docker Container Health (via SSH)"

# This section assumes we're running on the CI runner and can SSH to the host
# If running directly on the host, adjust accordingly
if command -v ssh &>/dev/null && [[ -f ~/.ssh/id_ed25519 ]]; then
  CONTAINERS=$(ssh -o StrictHostKeyChecking=no gabriel@"${HOST}" "cd /home/gabriel/police_scanner && docker compose ps --format '{{.Name}} {{.Status}}'" 2>/dev/null || echo "SSH_FAIL")
  if [[ "$CONTAINERS" == "SSH_FAIL" ]]; then
    fail "Docker health" "could not SSH to host"
  else
    ALL_HEALTHY=true
    while IFS= read -r line; do
      name=$(echo "$line" | awk '{print $1}')
      status=$(echo "$line" | cut -d' ' -f2-)
      if echo "$status" | grep -qiE 'up|healthy'; then
        pass "Container $name: $status"
      elif echo "$status" | grep -qi 'exited' && echo "$name" | grep -qi 'migrate'; then
        pass "Container $name: exited (migration expected)"
      else
        fail "Container $name" "$status"
        ALL_HEALTHY=false
      fi
    done <<< "$CONTAINERS"
  fi

  # DB migration check
  MIGRATE_STATUS=$(ssh -o StrictHostKeyChecking=no gabriel@"${HOST}" \
    "cd /home/gabriel/police_scanner && docker compose ps -a --format '{{.Name}} {{.ExitCode}}' | grep -i migrate" 2>/dev/null || echo "")
  if [[ -n "$MIGRATE_STATUS" ]]; then
    exit_code=$(echo "$MIGRATE_STATUS" | awk '{print $2}')
    [[ "$exit_code" == "0" ]] && pass "DB migration exited with code 0" || fail "DB migration" "exit code $exit_code"
  fi
fi

# ── Frontend ───────────────────────────────────────────────────────
section "Frontend Verification"

FRONTEND_RESP=$(curl -sf --max-time 10 "${FRONTEND}" 2>/dev/null || echo "")
FRONTEND_CODE=$(curl -sf -o /dev/null -w '%{http_code}' --max-time 10 "${FRONTEND}" 2>/dev/null || echo "000")

[[ "$FRONTEND_CODE" == "200" ]] && pass "Frontend returns 200" || fail "Frontend HTTP" "got $FRONTEND_CODE"

if echo "$FRONTEND_RESP" | grep -qi '<div id=\|<html\|<!doctype'; then
  pass "Frontend contains expected HTML"
else
  fail "Frontend HTML" "missing expected HTML content"
fi

# ── Summary ────────────────────────────────────────────────────────
section "SUMMARY"
echo ""
echo "Total: $TOTAL | Passed: $PASS | Failed: $FAIL"
echo ""

if [[ $FAIL -gt 0 ]]; then
  echo "🚫 STAGING GATE FAILED — $FAIL test(s) did not pass"
  exit 1
else
  echo "🎉 ALL STAGING TESTS PASSED — safe to promote to main"
  exit 0
fi
