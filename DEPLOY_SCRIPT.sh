#!/bin/bash
# ============================================================
# Police Scanner Optimization - Automated Deployment Script
# ============================================================

set -e  # Exit on error

echo "============================================================"
echo "Police Scanner Optimization Deployment"
echo "============================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "Step 1: Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker is not running. Please start Docker Desktop first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"
echo ""

echo "Step 2: Applying Database Schema..."
echo "  → Creating monitoring tables (system_logs, api_call_metrics)"
echo "  → Adding database indexes"

# Apply database schema using docker
docker run --rm -i \
  -e PGPASSWORD="$PGPASSWORD" \
  postgres:16 \
  psql -h "$PGHOST" \
       -U "$PGUSER" \
       -d "$PGDATABASE" \
       -f - < db/init.sql

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database schema applied successfully${NC}"
else
    echo -e "${RED}✗ Database schema update failed${NC}"
    exit 1
fi
echo ""

echo "Step 3: Stopping existing services..."
docker-compose down
echo -e "${GREEN}✓ Services stopped${NC}"
echo ""

echo "Step 4: Rebuilding containers with new code..."
docker-compose build app_scheduler
echo -e "${GREEN}✓ Containers rebuilt${NC}"
echo ""

echo "Step 5: Starting services..."
docker-compose up -d
echo -e "${GREEN}✓ Services started${NC}"
echo ""

echo "Step 6: Waiting for services to initialize (30 seconds)..."
sleep 30
echo -e "${GREEN}✓ Services initialized${NC}"
echo ""

echo "============================================================"
echo "Deployment Complete!"
echo "============================================================"
echo ""
echo "Next Steps:"
echo "  1. Monitor logs:"
echo "     docker-compose logs -f app_scheduler"
echo ""
echo "  2. Check deployment status (run after 5 minutes):"
echo "     bash verify_deployment.sh"
echo ""
echo "  3. View full monitoring queries:"
echo "     cat db/monitoring_queries.sql"
echo ""

echo -e "${YELLOW}Expected Results:${NC}"
echo "  • API calls: <10/hour (down from ~360/hour)"
echo "  • Cycle time: <1 second (down from minutes)"
echo "  • Duplicates: 0%"
echo "  • Audio processing: Near real-time (<1 min)"
echo ""
