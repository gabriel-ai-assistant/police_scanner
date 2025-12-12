#!/usr/bin/env bash

# Police Scanner Analytics Platform - Development Environment Setup
# This script sets up a complete local development environment

set -e  # Exit on error

echo "========================================="
echo "Police Scanner - Development Setup"
echo "========================================="
echo ""

# Check for required tools
echo "Checking prerequisites..."

command -v docker >/dev/null 2>&1 || { echo "Error: Docker is required but not installed. Please install Docker first."; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "Error: Docker Compose is required but not installed."; exit 1; }
command -v git >/dev/null 2>&1 || { echo "Error: Git is required but not installed."; exit 1; }

echo "✓ Docker found: $(docker --version)"
echo "✓ Docker Compose found: $(docker compose version)"
echo "✓ Git found: $(git --version)"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit .env with your actual credentials before continuing"
    echo ""
    echo "Required configuration:"
    echo "  - Database credentials (PGHOST, PGUSER, PGPASSWORD)"
    echo "  - Broadcastify API keys (BCFY_API_KEY, BCFY_API_KEY_ID, BCFY_APP_ID)"
    echo "  - MinIO credentials (MINIO_ENDPOINT, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD)"
    echo "  - MeiliSearch master key (MEILI_MASTER_KEY)"
    echo ""
    read -p "Press Enter after you've configured .env, or Ctrl+C to exit..."
fi

echo "✓ Environment file exists"
echo ""

# Pull latest images
echo "Pulling Docker images..."
docker compose pull
echo ""

# Build containers
echo "Building Docker containers..."
docker compose build
echo "✓ Containers built successfully"
echo ""

# Start services
echo "Starting services..."
docker compose up -d
echo "✓ Services started"
echo ""

# Wait for services to be healthy
echo "Waiting for services to be ready..."
sleep 10

# Check service health
echo "Checking service health..."

API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health || echo "000")
if [ "$API_HEALTH" = "200" ]; then
    echo "✓ API is healthy"
else
    echo "⚠️  API health check failed (HTTP $API_HEALTH)"
fi

MEILI_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:7700/health || echo "000")
if [ "$MEILI_HEALTH" = "200" ]; then
    echo "✓ MeiliSearch is healthy"
else
    echo "⚠️  MeiliSearch health check failed (HTTP $MEILI_HEALTH)"
fi

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Access points:"
echo "  Frontend:     http://localhost:80"
echo "  API:          http://localhost:8000"
echo "  API Docs:     http://localhost:8000/docs"
echo "  MeiliSearch:  http://localhost:7700"
echo ""
echo "Next steps:"
echo "  - View logs:        make logs"
echo "  - Run tests:        make test"
echo "  - Stop services:    make down"
echo ""
echo "For more information, see docs/guides/local-development.md"
echo ""
