#!/bin/bash
# ============================================================
# Run this script ON THE DOCKER HOST with sudo:
#   sudo bash remote_deploy.sh
# ============================================================

set -e

cd /opt/policescanner

echo "============================================================"
echo "Police Scanner - Deploying Optimizations"
echo "============================================================"

# Step 1: Configure git safe directory
echo "Step 1: Configuring git..."
git config --global --add safe.directory /opt/policescanner

# Step 2: Pull latest changes
echo "Step 2: Pulling latest changes from GitHub..."
git fetch origin
git checkout Fly-DB-Branch
git pull origin Fly-DB-Branch

echo "Files updated:"
ls -la app_scheduler/*.py | head -10
ls -la db/*.sql | head -5

# Step 3: Load environment variables
echo ""
echo "Step 3: Loading environment..."
export $(cat .env | grep -v '^#' | xargs)

# Step 4: Apply database schema
echo ""
echo "Step 4: Applying database schema..."
docker run --rm -i \
  -e PGPASSWORD="$PGPASSWORD" \
  postgres:16 \
  psql -h "$PGHOST" \
       -U "$PGUSER" \
       -d "$PGDATABASE" \
       -f - < db/init.sql 2>&1 | tail -20

echo "Database schema applied"

# Step 5: Restart services
echo ""
echo "Step 5: Restarting Docker services..."
docker-compose down
docker-compose build app_scheduler
docker-compose up -d

echo ""
echo "Step 6: Waiting for services (30s)..."
sleep 30

echo ""
echo "Step 7: Checking service status..."
docker-compose ps

echo ""
echo "Step 8: Recent logs..."
docker-compose logs --tail=15 app_scheduler

echo ""
echo "============================================================"
echo "DEPLOYMENT COMPLETE!"
echo "============================================================"
echo ""
echo "To monitor logs:"
echo "  docker-compose logs -f app_scheduler"
echo ""
echo "To verify deployment (run after 5 min):"
echo "  # From your Windows machine:"
echo "  bash verify_remote_deployment.sh"
echo ""
