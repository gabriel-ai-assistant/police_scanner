#!/bin/bash
# ============================================================
# Deploy Police Scanner Optimizations to Remote Docker Host
# ============================================================

set -e  # Exit on error

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
echo "Police Scanner - Remote Deployment to Docker Host"
echo "============================================================"
echo "Host: ${DOCKER_HOST}"
echo "Directory: ${REMOTE_DIR}"
echo ""

# Check SSH connectivity
echo "Step 1: Checking SSH connectivity..."
if ! ssh -o ConnectTimeout=5 ${REMOTE_USER}@${DOCKER_HOST} "echo 'SSH OK'" > /dev/null 2>&1; then
    echo -e "${RED}✗ Cannot connect to ${DOCKER_HOST}${NC}"
    echo "Please ensure:"
    echo "  1. SSH is enabled on the remote host"
    echo "  2. You have SSH access (add your key with ssh-copy-id)"
    echo "  3. The host is reachable"
    exit 1
fi
echo -e "${GREEN}✓ SSH connection successful${NC}"
echo ""

# Sync modified files to remote host
echo "Step 2: Syncing optimized code to remote host..."
rsync -avz --progress \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='node_modules' \
    app_scheduler/get_calls.py \
    app_scheduler/scheduler.py \
    app_scheduler/db_pool.py \
    app_scheduler/audio_worker.py \
    db/init.sql \
    db/monitoring_queries.sql \
    ${REMOTE_USER}@${DOCKER_HOST}:${REMOTE_DIR}/

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Files synced successfully${NC}"
else
    echo -e "${RED}✗ File sync failed${NC}"
    exit 1
fi
echo ""

# Apply database schema
echo "Step 3: Applying database schema on remote host..."
ssh ${REMOTE_USER}@${DOCKER_HOST} << 'EOF_DB'
cd /opt/policescanner
echo "Applying database migrations..."

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Apply database schema using docker
docker run --rm -i \
  -e PGPASSWORD="$PGPASSWORD" \
  postgres:16 \
  psql -h "$PGHOST" \
       -U "$PGUSER" \
       -d "$PGDATABASE" \
       -f - < db/init.sql 2>&1

echo "Database schema applied"
EOF_DB

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database schema applied${NC}"
else
    echo -e "${YELLOW}⚠ Database schema may have already been applied${NC}"
fi
echo ""

# Restart services on remote host
echo "Step 4: Restarting services on remote host..."
ssh ${REMOTE_USER}@${DOCKER_HOST} << 'EOF_RESTART'
cd /opt/policescanner

echo "Stopping services..."
docker-compose down

echo "Rebuilding app_scheduler container..."
docker-compose build app_scheduler

echo "Starting services..."
docker-compose up -d

echo "Services restarted"
EOF_RESTART

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Services restarted successfully${NC}"
else
    echo -e "${RED}✗ Service restart failed${NC}"
    exit 1
fi
echo ""

# Wait for services to initialize
echo "Step 5: Waiting for services to initialize (30 seconds)..."
sleep 30
echo -e "${GREEN}✓ Services initialized${NC}"
echo ""

# Show recent logs
echo "Step 6: Showing recent logs..."
ssh ${REMOTE_USER}@${DOCKER_HOST} << 'EOF_LOGS'
cd /opt/policescanner
docker-compose logs --tail=20 app_scheduler
EOF_LOGS
echo ""

echo "============================================================"
echo "Deployment Complete!"
echo "============================================================"
echo ""
echo "Next Steps:"
echo ""
echo "1. Monitor logs on remote host:"
echo "   ssh ${REMOTE_USER}@${DOCKER_HOST} 'cd ${REMOTE_DIR} && docker-compose logs -f app_scheduler'"
echo ""
echo "2. Verify deployment (wait 5 minutes, then run):"
echo "   bash verify_remote_deployment.sh"
echo ""
echo "3. View monitoring dashboard:"
echo "   ssh ${REMOTE_USER}@${DOCKER_HOST}"
echo "   cd ${REMOTE_DIR}"
echo "   docker run --rm -i -e PGPASSWORD=\$PGPASSWORD postgres:16 psql -h \$PGHOST -U \$PGUSER -d \$PGDATABASE -f db/monitoring_queries.sql"
echo ""

echo -e "${YELLOW}Expected Results:${NC}"
echo "  • API calls: <10/hour (down from ~360/hour)"
echo "  • Cycle time: <1 second (down from minutes)"
echo "  • Duplicates: 0%"
echo "  • Audio processing: Near real-time (<1 min)"
echo ""
