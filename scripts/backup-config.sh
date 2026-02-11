#!/usr/bin/env bash
# =============================================================================
# Police Scanner PostgreSQL Backup Configuration
# =============================================================================
# This file contains all configurable settings for the backup system.
# Source this file from backup-db.sh and restore-db.sh
# =============================================================================

# Project paths
PROJECT_DIR="/opt/policescanner"
SCRIPTS_DIR="${PROJECT_DIR}/scripts"
ENV_FILE="${PROJECT_DIR}/.env"

# Backup destination (external mount point)
BACKUP_BASE="/mnt/backups/policescanner/db"
BACKUP_DAILY_DIR="${BACKUP_BASE}/daily"
BACKUP_WEEKLY_DIR="${BACKUP_BASE}/weekly"
BACKUP_MONTHLY_DIR="${BACKUP_BASE}/monthly"
BACKUP_LATEST_LINK="${BACKUP_BASE}/latest.sql.gz"

# Docker settings
DOCKER_CONTAINER="scanner-postgres"
DOCKER_SERVICE="postgres"

# Retention policy (GFS - Grandfather-Father-Son)
RETAIN_DAILY=14      # Keep 14 daily backups (2 weeks)
RETAIN_WEEKLY=12     # Keep 12 weekly backups (3 months)
RETAIN_MONTHLY=0     # Keep monthly backups forever (0 = no limit)

# Backup settings
BACKUP_PREFIX="policescanner"
BACKUP_COMPRESSION_LEVEL=9   # gzip level 1-9
MIN_BACKUP_SIZE_KB=1         # Minimum valid backup size in KB
REQUIRED_TABLE_COUNT=5       # Minimum expected tables

# Disk space requirements
MIN_FREE_SPACE_MB=500        # Minimum free space required

# Logging
LOG_DIR="/var/log/policescanner"
LOG_FILE="${LOG_DIR}/backup.log"
LOG_MAX_SIZE_MB=50
LOG_RETAIN_DAYS=30

# Lock file to prevent concurrent runs
LOCK_FILE="/var/run/policescanner-backup.lock"
LOCK_TIMEOUT=3600            # Maximum lock wait time in seconds

# Optional: Prometheus metrics
# Set to empty string to disable
PROMETHEUS_METRICS_DIR="/var/lib/node_exporter/textfile_collector"
PROMETHEUS_METRICS_FILE="${PROMETHEUS_METRICS_DIR}/backup_policescanner.prom"

# Optional: Webhook alerting on failure
# Will be loaded from .env if set there: BACKUP_WEBHOOK_URL
WEBHOOK_URL=""

# Timeouts
PG_DUMP_TIMEOUT=3600         # pg_dump timeout in seconds
CONNECTION_TIMEOUT=30        # Database connection test timeout

# Exit codes
EXIT_SUCCESS=0
EXIT_MISSING_ENV=1
EXIT_MISSING_CREDENTIALS=2
EXIT_NO_BACKUP_METHOD=3
EXIT_DEST_NOT_MOUNTED=4
EXIT_INSUFFICIENT_SPACE=5
EXIT_BACKUP_TOO_SMALL=6
EXIT_GZIP_INTEGRITY_FAIL=7
EXIT_DB_CONNECTION_TIMEOUT=8
EXIT_LOCK_FAILURE=9
