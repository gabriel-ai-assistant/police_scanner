#!/usr/bin/env bash

# Police Scanner Analytics Platform - Deployment Script
# WARNING: This script deploys to production. Use with caution.

set -e  # Exit on error

echo "========================================="
echo "Police Scanner - Production Deployment"
echo "========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Safety check
echo -e "${YELLOW}WARNING: This will deploy to PRODUCTION${NC}"
echo ""
read -p "Are you sure you want to continue? (type 'yes' to confirm): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""

# Pre-deployment checklist
echo "Pre-deployment checklist:"
echo "------------------------"

CHECKS_PASSED=1

# Check if .env exists
if [ -f .env ]; then
    echo "✓ .env file exists"
else
    echo -e "${RED}✗ .env file missing${NC}"
    CHECKS_PASSED=0
fi

# Check if on correct branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
    echo "✓ On main branch ($CURRENT_BRANCH)"
else
    echo -e "${YELLOW}⚠ Not on main branch (current: $CURRENT_BRANCH)${NC}"
    read -p "Continue anyway? (yes/no): " CONTINUE_BRANCH
    if [ "$CONTINUE_BRANCH" != "yes" ]; then
        echo "Deployment cancelled."
        exit 0
    fi
fi

# Check for uncommitted changes
if [ -z "$(git status --porcelain)" ]; then
    echo "✓ No uncommitted changes"
else
    echo -e "${YELLOW}⚠ Uncommitted changes detected${NC}"
    git status --short
    read -p "Continue anyway? (yes/no): " CONTINUE_CHANGES
    if [ "$CONTINUE_CHANGES" != "yes" ]; then
        echo "Deployment cancelled."
        exit 0
    fi
fi

# Check Docker is running
if docker info >/dev/null 2>&1; then
    echo "✓ Docker is running"
else
    echo -e "${RED}✗ Docker is not running${NC}"
    CHECKS_PASSED=0
fi

echo ""

if [ $CHECKS_PASSED -eq 0 ]; then
    echo -e "${RED}Pre-deployment checks failed. Aborting.${NC}"
    exit 1
fi

# Run tests
echo "Running test suite..."
echo "--------------------"

if bash scripts/run-tests.sh; then
    echo -e "${GREEN}✓ All tests passed${NC}"
else
    echo -e "${RED}✗ Tests failed${NC}"
    read -p "Deploy anyway? (NOT RECOMMENDED - type 'yes' to confirm): " DEPLOY_ANYWAY
    if [ "$DEPLOY_ANYWAY" != "yes" ]; then
        echo "Deployment cancelled."
        exit 1
    fi
fi

echo ""

# Build containers
echo "Building production containers..."
echo "---------------------------------"

docker compose build --no-cache
echo -e "${GREEN}✓ Containers built${NC}"
echo ""

# Run database migrations
echo "Running database migrations..."
echo "------------------------------"

if [ -f db/scripts/execute-migrations.py ]; then
    python db/scripts/execute-migrations.py
    echo -e "${GREEN}✓ Migrations complete${NC}"
else
    echo -e "${YELLOW}⚠ Migration script not found, skipping${NC}"
fi

echo ""

# Pull latest changes
echo "Pulling latest code..."
echo "---------------------"

git pull origin $(git branch --show-current)
echo -e "${GREEN}✓ Code updated${NC}"
echo ""

# Stop current services
echo "Stopping current services..."
echo "---------------------------"

docker compose down
echo -e "${GREEN}✓ Services stopped${NC}"
echo ""

# Start new services
echo "Starting production services..."
echo "-------------------------------"

docker compose up -d
echo -e "${GREEN}✓ Services started${NC}"
echo ""

# Wait for services to be healthy
echo "Waiting for services to initialize..."
sleep 15

# Health checks
echo "Running health checks..."
echo "-----------------------"

API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health || echo "000")
if [ "$API_HEALTH" = "200" ]; then
    echo -e "${GREEN}✓ API is healthy${NC}"
else
    echo -e "${RED}✗ API health check failed (HTTP $API_HEALTH)${NC}"
fi

MEILI_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:7700/health || echo "000")
if [ "$MEILI_HEALTH" = "200" ]; then
    echo -e "${GREEN}✓ MeiliSearch is healthy${NC}"
else
    echo -e "${RED}✗ MeiliSearch health check failed (HTTP $MEILI_HEALTH)${NC}"
fi

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Services are now running in production mode."
echo ""
echo "Monitor logs with:"
echo "  docker compose logs -f"
echo ""
echo "Check service status:"
echo "  docker compose ps"
echo ""
