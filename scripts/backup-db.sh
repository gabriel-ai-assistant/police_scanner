#!/usr/bin/env bash
# =============================================================================
# Police Scanner PostgreSQL Database Backup Script
# =============================================================================
# Production-ready backup script with GFS rotation, verification, and alerting.
#
# Usage: backup-db.sh [OPTIONS]
#   --dry-run           Preview actions without executing
#   --verbose           Enable verbose output
#   --force-method=X    Force backup method: docker or direct
#   --help              Show this help message
#
# Exit codes defined in backup-config.sh
# =============================================================================

set -euo pipefail

# Get script directory for relative imports
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source configuration
source "${SCRIPT_DIR}/backup-config.sh"

# =============================================================================
# Globals
# =============================================================================
DRY_RUN=false
VERBOSE=false
FORCE_METHOD=""
BACKUP_METHOD=""
BACKUP_START_TIME=""
BACKUP_FILE=""
TEMP_BACKUP_FILE=""

# Database credentials (loaded from .env)
DB_HOST=""
DB_PORT=""
DB_USER=""
DB_PASS=""
DB_NAME=""

# =============================================================================
# Logging Functions
# =============================================================================
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Always log to file if log directory exists
    if [[ -d "${LOG_DIR}" ]]; then
        echo "[${timestamp}] [${level}] ${message}" >> "${LOG_FILE}" 2>/dev/null || true
    fi

    # Console output based on level and verbosity
    case "${level}" in
        ERROR|WARN)
            echo "[${level}] ${message}" >&2
            ;;
        INFO)
            echo "[${level}] ${message}"
            ;;
        DEBUG)
            if [[ "${VERBOSE}" == "true" ]]; then
                echo "[${level}] ${message}"
            fi
            ;;
    esac
}

log_info()  { log "INFO" "$@"; }
log_warn()  { log "WARN" "$@"; }
log_error() { log "ERROR" "$@"; }
log_debug() { log "DEBUG" "$@"; }

# =============================================================================
# Utility Functions
# =============================================================================
cleanup() {
    local exit_code=$?

    # Remove temp file if it exists
    if [[ -n "${TEMP_BACKUP_FILE}" && -f "${TEMP_BACKUP_FILE}" ]]; then
        rm -f "${TEMP_BACKUP_FILE}" 2>/dev/null || true
        log_debug "Cleaned up temp file: ${TEMP_BACKUP_FILE}"
    fi

    # Release lock
    release_lock

    # Calculate duration
    if [[ -n "${BACKUP_START_TIME}" ]]; then
        local end_time
        end_time=$(date +%s)
        local duration=$((end_time - BACKUP_START_TIME))
        log_info "Backup script completed in ${duration} seconds with exit code ${exit_code}"
    fi

    exit "${exit_code}"
}

trap cleanup EXIT

show_help() {
    cat << 'EOF'
Police Scanner PostgreSQL Database Backup Script

Usage: backup-db.sh [OPTIONS]

Options:
  --dry-run           Preview actions without executing
  --verbose           Enable verbose output
  --force-method=X    Force backup method: docker or direct
  --help              Show this help message

Examples:
  backup-db.sh                      # Normal backup
  backup-db.sh --verbose            # Backup with detailed output
  backup-db.sh --dry-run            # Preview without executing
  backup-db.sh --force-method=docker # Force Docker-based backup

Environment:
  Reads database credentials from /opt/policescanner/.env

GFS Rotation:
  - Daily backups: kept for 14 days
  - Weekly backups (Sunday): kept for 12 weeks
  - Monthly backups (1st of month): kept forever
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                log_info "Dry-run mode enabled"
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --force-method=*)
                FORCE_METHOD="${1#*=}"
                if [[ "${FORCE_METHOD}" != "docker" && "${FORCE_METHOD}" != "direct" ]]; then
                    log_error "Invalid method: ${FORCE_METHOD}. Use 'docker' or 'direct'"
                    exit 1
                fi
                log_info "Forcing backup method: ${FORCE_METHOD}"
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# =============================================================================
# Lock Management
# =============================================================================
acquire_lock() {
    log_debug "Acquiring lock: ${LOCK_FILE}"

    # Create lock directory if needed
    local lock_dir
    lock_dir=$(dirname "${LOCK_FILE}")
    if [[ ! -d "${lock_dir}" ]]; then
        mkdir -p "${lock_dir}" 2>/dev/null || true
    fi

    # Try to acquire lock with timeout
    local wait_time=0
    while [[ -f "${LOCK_FILE}" ]]; do
        local lock_pid
        lock_pid=$(cat "${LOCK_FILE}" 2>/dev/null || echo "")

        # Check if the process holding the lock is still running
        if [[ -n "${lock_pid}" ]] && kill -0 "${lock_pid}" 2>/dev/null; then
            if [[ ${wait_time} -ge ${LOCK_TIMEOUT} ]]; then
                log_error "Lock acquisition timeout after ${LOCK_TIMEOUT}s. Another backup may be running (PID: ${lock_pid})"
                exit ${EXIT_LOCK_FAILURE}
            fi
            log_debug "Waiting for lock (held by PID ${lock_pid})..."
            sleep 5
            wait_time=$((wait_time + 5))
        else
            # Stale lock, remove it
            log_warn "Removing stale lock file (PID ${lock_pid} not running)"
            rm -f "${LOCK_FILE}"
            break
        fi
    done

    # Write our PID
    echo $$ > "${LOCK_FILE}"
    log_debug "Lock acquired (PID: $$)"
}

release_lock() {
    if [[ -f "${LOCK_FILE}" ]]; then
        local lock_pid
        lock_pid=$(cat "${LOCK_FILE}" 2>/dev/null || echo "")
        if [[ "${lock_pid}" == "$$" ]]; then
            rm -f "${LOCK_FILE}"
            log_debug "Lock released"
        fi
    fi
}

# =============================================================================
# Environment Loading
# =============================================================================
load_credentials() {
    log_info "Loading credentials from ${ENV_FILE}"

    if [[ ! -f "${ENV_FILE}" ]]; then
        log_error "Environment file not found: ${ENV_FILE}"
        exit ${EXIT_MISSING_ENV}
    fi

    # Source the env file to get variables
    set -a
    # shellcheck source=/dev/null
    source "${ENV_FILE}"
    set +a

    # Load webhook URL if set in env
    if [[ -n "${BACKUP_WEBHOOK_URL:-}" ]]; then
        WEBHOOK_URL="${BACKUP_WEBHOOK_URL}"
    fi

    # Use standard PG* variables
    DB_HOST="${PGHOST:-}"
    DB_PORT="${PGPORT:-5432}"
    DB_USER="${PGUSER:-}"
    DB_PASS="${PGPASSWORD:-}"
    DB_NAME="${PGDATABASE:-}"

    # Validate we have credentials
    if [[ -z "${DB_USER}" || -z "${DB_PASS}" || -z "${DB_NAME}" ]]; then
        log_error "Missing database credentials in ${ENV_FILE}"
        log_error "Required: PGUSER, PGPASSWORD, PGDATABASE"
        exit ${EXIT_MISSING_CREDENTIALS}
    fi

    log_debug "Loaded credentials for database: ${DB_NAME} (user: ${DB_USER})"
}

# =============================================================================
# Pre-flight Checks
# =============================================================================
check_backup_destination() {
    log_info "Checking backup destination: ${BACKUP_BASE}"

    # Check if /mnt/backups is mounted (if it's a mount point)
    local mount_point="/mnt/backups"
    if [[ -d "${mount_point}" ]]; then
        if ! mountpoint -q "${mount_point}" 2>/dev/null; then
            # Not a mount point, but directory exists - check if it's writable
            if [[ ! -w "${mount_point}" ]]; then
                log_warn "${mount_point} is not a mount point and not writable"
                # Try to create backup in local directory as fallback
                BACKUP_BASE="${PROJECT_DIR}/backups/db"
                BACKUP_DAILY_DIR="${BACKUP_BASE}/daily"
                BACKUP_WEEKLY_DIR="${BACKUP_BASE}/weekly"
                BACKUP_MONTHLY_DIR="${BACKUP_BASE}/monthly"
                BACKUP_LATEST_LINK="${BACKUP_BASE}/latest.sql.gz"
                log_info "Using fallback backup location: ${BACKUP_BASE}"
            fi
        fi
    else
        # Mount point doesn't exist, use local fallback
        BACKUP_BASE="${PROJECT_DIR}/backups/db"
        BACKUP_DAILY_DIR="${BACKUP_BASE}/daily"
        BACKUP_WEEKLY_DIR="${BACKUP_BASE}/weekly"
        BACKUP_MONTHLY_DIR="${BACKUP_BASE}/monthly"
        BACKUP_LATEST_LINK="${BACKUP_BASE}/latest.sql.gz"
        log_info "Mount point not found, using fallback: ${BACKUP_BASE}"
    fi

    # Create directory structure
    if [[ "${DRY_RUN}" == "false" ]]; then
        mkdir -p "${BACKUP_DAILY_DIR}" "${BACKUP_WEEKLY_DIR}" "${BACKUP_MONTHLY_DIR}"
        log_debug "Created backup directories"
    else
        log_info "[DRY-RUN] Would create: ${BACKUP_DAILY_DIR}, ${BACKUP_WEEKLY_DIR}, ${BACKUP_MONTHLY_DIR}"
    fi

    # Check if writable
    if [[ "${DRY_RUN}" == "false" ]]; then
        if ! touch "${BACKUP_BASE}/.write_test" 2>/dev/null; then
            log_error "Backup destination not writable: ${BACKUP_BASE}"
            exit ${EXIT_DEST_NOT_MOUNTED}
        fi
        rm -f "${BACKUP_BASE}/.write_test"
    fi

    log_debug "Backup destination is ready"
}

check_disk_space() {
    log_info "Checking available disk space"

    # Get available space in MB
    local available_mb
    available_mb=$(df -BM "${BACKUP_BASE}" 2>/dev/null | awk 'NR==2 {gsub(/M/,"",$4); print $4}')

    if [[ -z "${available_mb}" ]]; then
        log_warn "Could not determine available disk space"
        return 0
    fi

    log_debug "Available space: ${available_mb} MB (minimum: ${MIN_FREE_SPACE_MB} MB)"

    if [[ ${available_mb} -lt ${MIN_FREE_SPACE_MB} ]]; then
        log_error "Insufficient disk space: ${available_mb} MB available, ${MIN_FREE_SPACE_MB} MB required"
        exit ${EXIT_INSUFFICIENT_SPACE}
    fi

    log_info "Disk space OK: ${available_mb} MB available"
}

# =============================================================================
# Backup Method Detection
# =============================================================================
detect_backup_method() {
    log_info "Detecting backup method"

    if [[ -n "${FORCE_METHOD}" ]]; then
        BACKUP_METHOD="${FORCE_METHOD}"
        log_info "Using forced method: ${BACKUP_METHOD}"
        return 0
    fi

    # Check if Docker container is running
    if command -v docker &>/dev/null; then
        local container_status
        container_status=$(docker ps --filter "name=${DOCKER_CONTAINER}" --format "{{.Status}}" 2>/dev/null || echo "")

        if [[ "${container_status}" == *"Up"* ]]; then
            BACKUP_METHOD="docker"
            log_info "Docker container '${DOCKER_CONTAINER}' is running - using Docker method"
            return 0
        fi
        log_debug "Docker container '${DOCKER_CONTAINER}' not running"
    fi

    # Check if direct pg_dump is available
    if command -v pg_dump &>/dev/null; then
        BACKUP_METHOD="direct"
        log_info "pg_dump available - using direct method"
        return 0
    fi

    log_error "No backup method available. Need either:"
    log_error "  1. Docker container '${DOCKER_CONTAINER}' running, or"
    log_error "  2. pg_dump installed locally"
    exit ${EXIT_NO_BACKUP_METHOD}
}

test_database_connection() {
    log_info "Testing database connection"

    local test_cmd
    local result

    if [[ "${BACKUP_METHOD}" == "docker" ]]; then
        test_cmd="docker exec ${DOCKER_CONTAINER} pg_isready -U ${DB_USER} -d ${DB_NAME}"
    else
        test_cmd="PGPASSWORD='${DB_PASS}' pg_isready -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME}"
    fi

    if [[ "${DRY_RUN}" == "true" ]]; then
        log_info "[DRY-RUN] Would test connection with: ${test_cmd//${DB_PASS}/***}"
        return 0
    fi

    if timeout "${CONNECTION_TIMEOUT}" bash -c "${test_cmd}" &>/dev/null; then
        log_info "Database connection successful"
    else
        log_error "Database connection failed (timeout: ${CONNECTION_TIMEOUT}s)"
        exit ${EXIT_DB_CONNECTION_TIMEOUT}
    fi
}

# =============================================================================
# Backup Execution
# =============================================================================
execute_backup() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d_%H%M%S')
    local backup_filename="${BACKUP_PREFIX}_daily_${timestamp}.sql.gz"
    TEMP_BACKUP_FILE="${BACKUP_BASE}/.${backup_filename}.tmp"
    BACKUP_FILE="${BACKUP_DAILY_DIR}/${backup_filename}"

    log_info "Starting backup: ${backup_filename}"
    log_debug "Temp file: ${TEMP_BACKUP_FILE}"
    log_debug "Final file: ${BACKUP_FILE}"

    if [[ "${DRY_RUN}" == "true" ]]; then
        log_info "[DRY-RUN] Would create backup: ${BACKUP_FILE}"
        return 0
    fi

    local dump_cmd
    if [[ "${BACKUP_METHOD}" == "docker" ]]; then
        dump_cmd="docker exec ${DOCKER_CONTAINER} pg_dump -U ${DB_USER} ${DB_NAME}"
    else
        dump_cmd="PGPASSWORD='${DB_PASS}' pg_dump -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} ${DB_NAME}"
    fi

    log_debug "Executing: ${dump_cmd//${DB_PASS}/***} | gzip -${BACKUP_COMPRESSION_LEVEL}"

    # Execute backup with timeout
    if ! timeout "${PG_DUMP_TIMEOUT}" bash -c "${dump_cmd}" 2>/dev/null | gzip -"${BACKUP_COMPRESSION_LEVEL}" > "${TEMP_BACKUP_FILE}"; then
        log_error "pg_dump failed"
        rm -f "${TEMP_BACKUP_FILE}" 2>/dev/null || true
        exit ${EXIT_BACKUP_TOO_SMALL}
    fi

    log_info "Backup created: $(du -h "${TEMP_BACKUP_FILE}" | cut -f1)"
}

# =============================================================================
# Backup Verification
# =============================================================================
verify_backup() {
    log_info "Verifying backup integrity"

    if [[ "${DRY_RUN}" == "true" ]]; then
        log_info "[DRY-RUN] Would verify backup integrity"
        return 0
    fi

    # Check file exists
    if [[ ! -f "${TEMP_BACKUP_FILE}" ]]; then
        log_error "Backup file not found: ${TEMP_BACKUP_FILE}"
        exit ${EXIT_BACKUP_TOO_SMALL}
    fi

    # Check minimum size
    local file_size_kb
    file_size_kb=$(du -k "${TEMP_BACKUP_FILE}" | cut -f1)
    if [[ ${file_size_kb} -lt ${MIN_BACKUP_SIZE_KB} ]]; then
        log_error "Backup too small: ${file_size_kb} KB (minimum: ${MIN_BACKUP_SIZE_KB} KB)"
        exit ${EXIT_BACKUP_TOO_SMALL}
    fi
    log_debug "Backup size: ${file_size_kb} KB"

    # Gzip integrity check
    if ! gzip -t "${TEMP_BACKUP_FILE}" 2>/dev/null; then
        log_error "Gzip integrity check failed"
        exit ${EXIT_GZIP_INTEGRITY_FAIL}
    fi
    log_debug "Gzip integrity: OK"

    # Count tables in backup
    local table_count
    table_count=$(zcat "${TEMP_BACKUP_FILE}" 2>/dev/null | grep -c "^CREATE TABLE" || echo "0")
    if [[ ${table_count} -lt ${REQUIRED_TABLE_COUNT} ]]; then
        log_warn "Found only ${table_count} tables (expected at least ${REQUIRED_TABLE_COUNT})"
    else
        log_debug "Table count: ${table_count}"
    fi

    log_info "Backup verification passed"
}

# =============================================================================
# GFS Rotation
# =============================================================================
rotate_backups() {
    log_info "Applying GFS rotation"

    if [[ "${DRY_RUN}" == "true" ]]; then
        log_info "[DRY-RUN] Would apply GFS rotation"
        return 0
    fi

    # Move temp file to daily
    mv "${TEMP_BACKUP_FILE}" "${BACKUP_FILE}"
    TEMP_BACKUP_FILE=""  # Clear so cleanup doesn't try to remove it
    log_info "Saved daily backup: ${BACKUP_FILE}"

    local day_of_week
    local day_of_month
    day_of_week=$(date '+%u')  # 1=Monday, 7=Sunday
    day_of_month=$(date '+%d')

    local base_filename
    base_filename=$(basename "${BACKUP_FILE}")

    # Weekly backup (Sunday = day 7)
    if [[ "${day_of_week}" == "7" ]]; then
        local weekly_filename="${BACKUP_PREFIX}_weekly_$(date '+%Y-%m-%d_%H%M%S').sql.gz"
        cp "${BACKUP_FILE}" "${BACKUP_WEEKLY_DIR}/${weekly_filename}"
        log_info "Saved weekly backup: ${weekly_filename}"
    fi

    # Monthly backup (1st of month)
    if [[ "${day_of_month}" == "01" ]]; then
        local monthly_filename="${BACKUP_PREFIX}_monthly_$(date '+%Y-%m-%d_%H%M%S').sql.gz"
        cp "${BACKUP_FILE}" "${BACKUP_MONTHLY_DIR}/${monthly_filename}"
        log_info "Saved monthly backup: ${monthly_filename}"
    fi

    # Update latest symlink
    ln -sf "${BACKUP_FILE}" "${BACKUP_LATEST_LINK}"
    log_debug "Updated latest symlink: ${BACKUP_LATEST_LINK}"
}

prune_old_backups() {
    log_info "Pruning old backups"

    if [[ "${DRY_RUN}" == "true" ]]; then
        log_info "[DRY-RUN] Would prune old backups"
        return 0
    fi

    local count_before count_after pruned

    # Prune daily backups
    if [[ ${RETAIN_DAILY} -gt 0 ]]; then
        count_before=$(find "${BACKUP_DAILY_DIR}" -name "${BACKUP_PREFIX}_daily_*.sql.gz" -type f 2>/dev/null | wc -l)
        find "${BACKUP_DAILY_DIR}" -name "${BACKUP_PREFIX}_daily_*.sql.gz" -type f -mtime +${RETAIN_DAILY} -delete 2>/dev/null || true
        count_after=$(find "${BACKUP_DAILY_DIR}" -name "${BACKUP_PREFIX}_daily_*.sql.gz" -type f 2>/dev/null | wc -l)
        pruned=$((count_before - count_after))
        if [[ ${pruned} -gt 0 ]]; then
            log_info "Pruned ${pruned} daily backup(s) older than ${RETAIN_DAILY} days"
        fi
    fi

    # Prune weekly backups
    if [[ ${RETAIN_WEEKLY} -gt 0 ]]; then
        local retain_weeks_days=$((RETAIN_WEEKLY * 7))
        count_before=$(find "${BACKUP_WEEKLY_DIR}" -name "${BACKUP_PREFIX}_weekly_*.sql.gz" -type f 2>/dev/null | wc -l)
        find "${BACKUP_WEEKLY_DIR}" -name "${BACKUP_PREFIX}_weekly_*.sql.gz" -type f -mtime +${retain_weeks_days} -delete 2>/dev/null || true
        count_after=$(find "${BACKUP_WEEKLY_DIR}" -name "${BACKUP_PREFIX}_weekly_*.sql.gz" -type f 2>/dev/null | wc -l)
        pruned=$((count_before - count_after))
        if [[ ${pruned} -gt 0 ]]; then
            log_info "Pruned ${pruned} weekly backup(s) older than ${RETAIN_WEEKLY} weeks"
        fi
    fi

    # Monthly backups: only prune if RETAIN_MONTHLY > 0
    if [[ ${RETAIN_MONTHLY} -gt 0 ]]; then
        local retain_months_days=$((RETAIN_MONTHLY * 30))
        count_before=$(find "${BACKUP_MONTHLY_DIR}" -name "${BACKUP_PREFIX}_monthly_*.sql.gz" -type f 2>/dev/null | wc -l)
        find "${BACKUP_MONTHLY_DIR}" -name "${BACKUP_PREFIX}_monthly_*.sql.gz" -type f -mtime +${retain_months_days} -delete 2>/dev/null || true
        count_after=$(find "${BACKUP_MONTHLY_DIR}" -name "${BACKUP_PREFIX}_monthly_*.sql.gz" -type f 2>/dev/null | wc -l)
        pruned=$((count_before - count_after))
        if [[ ${pruned} -gt 0 ]]; then
            log_info "Pruned ${pruned} monthly backup(s) older than ${RETAIN_MONTHLY} months"
        fi
    fi
}

# =============================================================================
# Metrics & Alerting
# =============================================================================
write_prometheus_metrics() {
    if [[ -z "${PROMETHEUS_METRICS_FILE}" ]]; then
        return 0
    fi

    log_debug "Writing Prometheus metrics to ${PROMETHEUS_METRICS_FILE}"

    if [[ "${DRY_RUN}" == "true" ]]; then
        log_info "[DRY-RUN] Would write Prometheus metrics"
        return 0
    fi

    # Create metrics directory if needed
    local metrics_dir
    metrics_dir=$(dirname "${PROMETHEUS_METRICS_FILE}")
    if [[ ! -d "${metrics_dir}" ]]; then
        mkdir -p "${metrics_dir}" 2>/dev/null || {
            log_debug "Could not create metrics directory: ${metrics_dir}"
            return 0
        }
    fi

    local backup_size=0
    local duration=0
    local end_time
    end_time=$(date +%s)

    if [[ -n "${BACKUP_START_TIME}" ]]; then
        duration=$((end_time - BACKUP_START_TIME))
    fi

    if [[ -f "${BACKUP_FILE}" ]]; then
        backup_size=$(stat -c%s "${BACKUP_FILE}" 2>/dev/null || echo "0")
    fi

    local daily_count weekly_count monthly_count
    daily_count=$(find "${BACKUP_DAILY_DIR}" -name "*.sql.gz" -type f 2>/dev/null | wc -l)
    weekly_count=$(find "${BACKUP_WEEKLY_DIR}" -name "*.sql.gz" -type f 2>/dev/null | wc -l)
    monthly_count=$(find "${BACKUP_MONTHLY_DIR}" -name "*.sql.gz" -type f 2>/dev/null | wc -l)

    cat > "${PROMETHEUS_METRICS_FILE}.tmp" << EOF
# HELP policescanner_backup_success Whether the last backup was successful (1=success, 0=failure)
# TYPE policescanner_backup_success gauge
policescanner_backup_success 1
# HELP policescanner_backup_last_timestamp Unix timestamp of the last successful backup
# TYPE policescanner_backup_last_timestamp gauge
policescanner_backup_last_timestamp ${end_time}
# HELP policescanner_backup_last_size_bytes Size of the last backup in bytes
# TYPE policescanner_backup_last_size_bytes gauge
policescanner_backup_last_size_bytes ${backup_size}
# HELP policescanner_backup_duration_seconds Duration of the last backup in seconds
# TYPE policescanner_backup_duration_seconds gauge
policescanner_backup_duration_seconds ${duration}
# HELP policescanner_backup_daily_count Number of daily backups
# TYPE policescanner_backup_daily_count gauge
policescanner_backup_daily_count ${daily_count}
# HELP policescanner_backup_weekly_count Number of weekly backups
# TYPE policescanner_backup_weekly_count gauge
policescanner_backup_weekly_count ${weekly_count}
# HELP policescanner_backup_monthly_count Number of monthly backups
# TYPE policescanner_backup_monthly_count gauge
policescanner_backup_monthly_count ${monthly_count}
EOF

    mv "${PROMETHEUS_METRICS_FILE}.tmp" "${PROMETHEUS_METRICS_FILE}"
    log_debug "Prometheus metrics written"
}

send_failure_webhook() {
    local error_message="$1"

    if [[ -z "${WEBHOOK_URL}" ]]; then
        return 0
    fi

    log_info "Sending failure webhook"

    local payload
    payload=$(cat << EOF
{
    "status": "failed",
    "error": "${error_message}",
    "timestamp": "$(date -Iseconds)",
    "host": "$(hostname)",
    "database": "${DB_NAME}"
}
EOF
)

    if command -v curl &>/dev/null; then
        curl -s -X POST -H "Content-Type: application/json" -d "${payload}" "${WEBHOOK_URL}" &>/dev/null || true
    fi
}

# =============================================================================
# Main Entry Point
# =============================================================================
main() {
    BACKUP_START_TIME=$(date +%s)

    parse_args "$@"

    log_info "=========================================="
    log_info "Police Scanner Database Backup Starting"
    log_info "=========================================="
    log_info "Date: $(date)"
    log_info "Host: $(hostname)"

    # Acquire lock first
    acquire_lock

    # Load and validate configuration
    load_credentials

    # Pre-flight checks
    check_backup_destination
    check_disk_space

    # Detect and test backup method
    detect_backup_method
    test_database_connection

    # Execute backup
    execute_backup
    verify_backup

    # GFS rotation
    rotate_backups
    prune_old_backups

    # Metrics
    write_prometheus_metrics

    log_info "=========================================="
    log_info "Backup completed successfully"
    log_info "=========================================="

    exit ${EXIT_SUCCESS}
}

# Run main function
main "$@"
