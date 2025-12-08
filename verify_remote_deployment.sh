#!/bin/bash
# ============================================================
# Verify Police Scanner Deployment on Remote Docker Host
# ============================================================

# Remote host configuration
DOCKER_HOST="192.168.1.120"
REMOTE_USER="root"  # Change if needed
REMOTE_DIR="/opt/policescanner"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "============================================================"
echo "Police Scanner Deployment Verification (Remote)"
echo "============================================================"
echo "Host: ${DOCKER_HOST}"
echo ""

# Run verification on remote host
ssh ${REMOTE_USER}@${DOCKER_HOST} << 'EOF_VERIFY'
cd /opt/policescanner

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Function to run SQL query
run_query() {
    docker run --rm -i \
      -e PGPASSWORD="$PGPASSWORD" \
      postgres:16 \
      psql -h "$PGHOST" \
           -U "$PGUSER" \
           -d "$PGDATABASE" \
           -t -c "$1" 2>/dev/null
}

# Check 1: API Call Rate
echo "1. Checking API call rate (last hour)..."
API_CALLS=$(run_query "SELECT COUNT(*) FROM api_call_metrics WHERE timestamp > NOW() - INTERVAL '1 hour';")
API_CALLS=$(echo $API_CALLS | tr -d ' ')

if [ -z "$API_CALLS" ]; then
    echo -e "${YELLOW}⚠ No API call data yet (table may be empty)${NC}"
elif [ "$API_CALLS" -lt 10 ]; then
    echo -e "${GREEN}✓ API calls: $API_CALLS/hour (EXCELLENT - target <10)${NC}"
elif [ "$API_CALLS" -lt 20 ]; then
    echo -e "${YELLOW}⚠ API calls: $API_CALLS/hour (OK - target <10)${NC}"
else
    echo -e "${RED}✗ API calls: $API_CALLS/hour (TOO HIGH - target <10)${NC}"
fi
echo ""

# Check 2: Duplicate Calls
echo "2. Checking for duplicate calls (last hour)..."
DUPLICATES=$(run_query "SELECT COUNT(*) FROM (SELECT call_uid FROM bcfy_calls_raw WHERE fetched_at > NOW() - INTERVAL '1 hour' GROUP BY call_uid HAVING COUNT(*) > 1) dups;")
DUPLICATES=$(echo $DUPLICATES | tr -d ' ')

if [ -z "$DUPLICATES" ]; then
    echo -e "${YELLOW}⚠ No call data yet${NC}"
elif [ "$DUPLICATES" -eq 0 ]; then
    echo -e "${GREEN}✓ Duplicates: 0 (PERFECT)${NC}"
else
    echo -e "${RED}✗ Duplicates: $DUPLICATES (should be 0)${NC}"
fi
echo ""

# Check 3: Audio Processing Backlog
echo "3. Checking audio processing backlog..."
BACKLOG=$(run_query "SELECT COUNT(*) FROM bcfy_calls_raw WHERE processed = FALSE AND error IS NULL;")
BACKLOG=$(echo $BACKLOG | tr -d ' ')

if [ -z "$BACKLOG" ]; then
    echo -e "${YELLOW}⚠ No call data yet${NC}"
elif [ "$BACKLOG" -lt 100 ]; then
    echo -e "${GREEN}✓ Pending audio: $BACKLOG (EXCELLENT - near real-time)${NC}"
elif [ "$BACKLOG" -lt 500 ]; then
    echo -e "${YELLOW}⚠ Pending audio: $BACKLOG (backlog growing)${NC}"
else
    echo -e "${RED}✗ Pending audio: $BACKLOG (large backlog - check worker)${NC}"
fi
echo ""

# Check 4: Ingestion Cycle Performance
echo "4. Checking ingestion cycle performance (last hour)..."
AVG_CYCLE=$(run_query "SELECT ROUND(AVG(duration_ms)) FROM system_logs WHERE component = 'ingestion' AND event_type = 'cycle_complete' AND timestamp > NOW() - INTERVAL '1 hour';")
AVG_CYCLE=$(echo $AVG_CYCLE | tr -d ' ')

if [ -z "$AVG_CYCLE" ] || [ "$AVG_CYCLE" == "" ]; then
    echo -e "${YELLOW}⚠ No cycle data yet${NC}"
elif [ "$AVG_CYCLE" -lt 5000 ]; then
    echo -e "${GREEN}✓ Average cycle time: ${AVG_CYCLE}ms (FAST - target <5000ms)${NC}"
elif [ "$AVG_CYCLE" -lt 10000 ]; then
    echo -e "${YELLOW}⚠ Average cycle time: ${AVG_CYCLE}ms (OK)${NC}"
else
    echo -e "${RED}✗ Average cycle time: ${AVG_CYCLE}ms (SLOW)${NC}"
fi
echo ""

# Check 5: Last Seen Updates
echo "5. Checking last_seen timestamp freshness..."
run_query "SELECT name, TO_TIMESTAMP(last_seen) as last_seen_time, NOW() - TO_TIMESTAMP(last_seen) as staleness FROM bcfy_playlists WHERE sync = TRUE ORDER BY last_seen DESC LIMIT 3;" | head -5
echo ""

# Check 6: Recent Errors
echo "6. Checking for recent errors..."
ERROR_COUNT=$(run_query "SELECT COUNT(*) FROM system_logs WHERE severity = 'ERROR' AND timestamp > NOW() - INTERVAL '1 hour';")
ERROR_COUNT=$(echo $ERROR_COUNT | tr -d ' ')

if [ -z "$ERROR_COUNT" ]; then
    echo -e "${YELLOW}⚠ No log data yet${NC}"
elif [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓ No errors in last hour${NC}"
else
    echo -e "${RED}✗ Found $ERROR_COUNT errors in last hour${NC}"
    echo "Recent errors:"
    run_query "SELECT timestamp, message FROM system_logs WHERE severity = 'ERROR' AND timestamp > NOW() - INTERVAL '1 hour' ORDER BY timestamp DESC LIMIT 5;"
fi
echo ""

# Check 7: Docker Container Status
echo "7. Checking Docker container status..."
docker-compose ps app_scheduler
echo ""

echo "============================================================"
echo "Summary"
echo "============================================================"

# Overall health score
HEALTH_SCORE=0
[ -n "$API_CALLS" ] && [ "$API_CALLS" -lt 10 ] && HEALTH_SCORE=$((HEALTH_SCORE + 1))
[ -n "$DUPLICATES" ] && [ "$DUPLICATES" -eq 0 ] && HEALTH_SCORE=$((HEALTH_SCORE + 1))
[ -n "$BACKLOG" ] && [ "$BACKLOG" -lt 100 ] && HEALTH_SCORE=$((HEALTH_SCORE + 1))
[ -n "$AVG_CYCLE" ] && [ "$AVG_CYCLE" != "" ] && [ "$AVG_CYCLE" -lt 5000 ] && HEALTH_SCORE=$((HEALTH_SCORE + 1))
[ -n "$ERROR_COUNT" ] && [ "$ERROR_COUNT" -eq 0 ] && HEALTH_SCORE=$((HEALTH_SCORE + 1))

if [ $HEALTH_SCORE -ge 4 ]; then
    echo -e "${GREEN}✓ Deployment Status: HEALTHY (${HEALTH_SCORE}/5 checks passed)${NC}"
elif [ $HEALTH_SCORE -ge 2 ]; then
    echo -e "${YELLOW}⚠ Deployment Status: NEEDS ATTENTION (${HEALTH_SCORE}/5 checks passed)${NC}"
else
    echo -e "${RED}✗ Deployment Status: ISSUES DETECTED (${HEALTH_SCORE}/5 checks passed)${NC}"
fi

echo ""
echo "For detailed monitoring, run on remote host:"
echo "  cd /opt/policescanner"
echo "  docker run --rm -i -e PGPASSWORD=\$PGPASSWORD postgres:16 psql -h \$PGHOST -U \$PGUSER -d \$PGDATABASE -f db/monitoring_queries.sql"
echo ""
EOF_VERIFY

echo ""
echo "To view live logs:"
echo "  ssh ${REMOTE_USER}@${DOCKER_HOST} 'cd ${REMOTE_DIR} && docker-compose logs -f app_scheduler'"
echo ""
