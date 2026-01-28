#!/usr/bin/env bash
# =============================================================================
# Police Scanner PostgreSQL Database Restore Script
# =============================================================================
# Restores a PostgreSQL database from a backup file with safety measures.
#
# Usage: restore-db.sh [OPTIONS] <backup_file|latest>
#   --dry-run         Preview restore without executing
#   --force-method=X  Force restore method: docker or direct
#   --drop-existing   Drop existing objects before restore
#   --no-confirm      Skip interactive confirmation (dangerous)
#   --create-backup   Backup current state before restore
#   --target-db=NAME  Restore to a different database
#   --help            Show this help message
#
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
DROP_EXISTING=false
NO_CONFIRM=false
CREATE_BACKUP=false
TARGET_DB=""
RESTORE_METHOD=""
BACKUP_FILE_PATH=""

# Database credentials
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
show_help() {
    cat << 'EOF'
Police Scanner PostgreSQL Database Restore Script

Usage: restore-db.sh [OPTIONS] <backup_file|latest>

Arguments:
  backup_file       Path to the backup file (.sql.gz)
  latest            Use the most recent backup (via latest.sql.gz symlink)

Options:
  --dry-run         Preview restore without executing
  --verbose         Enable verbose output
  --force-method=X  Force restore method: docker or direct
  --drop-existing   Drop existing database objects before restore
  --no-confirm      Skip interactive confirmation (DANGEROUS)
  --create-backup   Create backup of current state before restoring
  --target-db=NAME  Restore to a different database name
  --help            Show this help message

Examples:
  restore-db.sh latest                         # Restore from latest backup
  restore-db.sh /mnt/backups/.../backup.sql.gz # Restore specific backup
  restore-db.sh --dry-run latest               # Preview restore
  restore-db.sh --create-backup latest         # Backup first, then restore
  restore-db.sh --target-db=scanner_test latest # Restore to different DB

Safety:
  - By default, requires interactive confirmation
  - Use --create-backup to save current state first
  - Use --dry-run to preview actions
  - Use --no-confirm only in automated scripts with caution

EOF
}

parse_args() {
    local positional_args=()

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
                shift
                ;;
            --drop-existing)
                DROP_EXISTING=true
                shift
                ;;
            --no-confirm)
                NO_CONFIRM=true
                log_warn "Confirmation disabled - restore will proceed without prompts"
                shift
                ;;
            --create-backup)
                CREATE_BACKUP=true
                shift
                ;;
            --target-db=*)
                TARGET_DB="${1#*=}"
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            -*)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
            *)
                positional_args+=("$1")
                shift
                ;;
        esac
    done

    if [[ ${#positional_args[@]} -eq 0 ]]; then
        log_error "Backup file argument required"
        show_help
        exit 1
    fi

    BACKUP_FILE_PATH="${positional_args[0]}"
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

    set -a
    # shellcheck source=/dev/null
    source "${ENV_FILE}"
    set +a

    DB_HOST="${PGHOST:-}"
    DB_PORT="${PGPORT:-5432}"
    DB_USER="${PGUSER:-}"
    DB_PASS="${PGPASSWORD:-}"
    DB_NAME="${PGDATABASE:-}"

    # Use target database if specified
    if [[ -n "${TARGET_DB}" ]]; then
        DB_NAME="${TARGET_DB}"
        log_info "Using target database: ${DB_NAME}"
    fi

    if [[ -z "${DB_USER}" || -z "${DB_PASS}" || -z "${DB_NAME}" ]]; then
        log_error "Missing database credentials"
        exit ${EXIT_MISSING_CREDENTIALS}
    fi

    log_debug "Database: ${DB_NAME} (user: ${DB_USER})"
}

# =============================================================================
# Backup File Resolution
# =============================================================================
resolve_backup_file() {
    log_info "Resolving backup file: ${BACKUP_FILE_PATH}"

    # Handle "latest" keyword
    if [[ "${BACKUP_FILE_PATH}" == "latest" ]]; then
        # Check both possible locations
        if [[ -L "${BACKUP_LATEST_LINK}" ]]; then
            BACKUP_FILE_PATH=$(readlink -f "${BACKUP_LATEST_LINK}")
        elif [[ -L "${PROJECT_DIR}/backups/db/latest.sql.gz" ]]; then
            BACKUP_FILE_PATH=$(readlink -f "${PROJECT_DIR}/backups/db/latest.sql.gz")
        else
            log_error "No 'latest' backup symlink found"
            log_error "Checked: ${BACKUP_LATEST_LINK}"
            log_error "Checked: ${PROJECT_DIR}/backups/db/latest.sql.gz"
            exit 1
        fi
        log_info "Resolved 'latest' to: ${BACKUP_FILE_PATH}"
    fi

    # Verify file exists
    if [[ ! -f "${BACKUP_FILE_PATH}" ]]; then
        log_error "Backup file not found: ${BACKUP_FILE_PATH}"
        exit 1
    fi

    # Verify it's a gzip file
    if [[ "${BACKUP_FILE_PATH}" != *.gz ]]; then
        log_warn "Backup file doesn't have .gz extension - assuming compressed anyway"
    fi
}

verify_backup_file() {
    log_info "Verifying backup file integrity"

    # Gzip integrity check
    if ! gzip -t "${BACKUP_FILE_PATH}" 2>/dev/null; then
        log_error "Backup file failed gzip integrity check: ${BACKUP_FILE_PATH}"
        exit ${EXIT_GZIP_INTEGRITY_FAIL}
    fi
    log_debug "Gzip integrity: OK"

    # Get file info
    local file_size
    file_size=$(du -h "${BACKUP_FILE_PATH}" | cut -f1)
    local file_date
    file_date=$(stat -c '%y' "${BACKUP_FILE_PATH}" 2>/dev/null | cut -d'.' -f1)
    local table_count
    table_count=$(zcat "${BACKUP_FILE_PATH}" 2>/dev/null | grep -c "^CREATE TABLE" || echo "0")

    log_info "Backup file details:"
    log_info "  Path: ${BACKUP_FILE_PATH}"
    log_info "  Size: ${file_size}"
    log_info "  Date: ${file_date}"
    log_info "  Tables: ${table_count}"
}

# =============================================================================
# Restore Method Detection
# =============================================================================
detect_restore_method() {
    log_info "Detecting restore method"

    if [[ -n "${FORCE_METHOD}" ]]; then
        RESTORE_METHOD="${FORCE_METHOD}"
        log_info "Using forced method: ${RESTORE_METHOD}"
        return 0
    fi

    # Check Docker container
    if command -v docker &>/dev/null; then
        local container_status
        container_status=$(docker ps --filter "name=${DOCKER_CONTAINER}" --format "{{.Status}}" 2>/dev/null || echo "")

        if [[ "${container_status}" == *"Up"* ]]; then
            RESTORE_METHOD="docker"
            log_info "Docker container running - using Docker method"
            return 0
        fi
    fi

    # Check direct psql
    if command -v psql &>/dev/null; then
        RESTORE_METHOD="direct"
        log_info "psql available - using direct method"
        return 0
    fi

    log_error "No restore method available"
    exit ${EXIT_NO_BACKUP_METHOD}
}

# =============================================================================
# Pre-restore Operations
# =============================================================================
show_target_info() {
    log_info "Target database information:"

    local db_info_cmd
    if [[ "${RESTORE_METHOD}" == "docker" ]]; then
        db_info_cmd="docker exec ${DOCKER_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -c \"SELECT current_database(), pg_size_pretty(pg_database_size(current_database())), (SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public');\""
    else
        db_info_cmd="PGPASSWORD='${DB_PASS}' psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -c \"SELECT current_database(), pg_size_pretty(pg_database_size(current_database())), (SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public');\""
    fi

    log_debug "Query: ${db_info_cmd//${DB_PASS}/***}"

    if [[ "${DRY_RUN}" == "false" ]]; then
        local result
        result=$(eval "${db_info_cmd}" 2>/dev/null || echo "Could not query database")
        echo "${result}"
    else
        log_info "[DRY-RUN] Would query database info"
    fi
}

confirm_restore() {
    if [[ "${NO_CONFIRM}" == "true" ]]; then
        log_warn "Skipping confirmation (--no-confirm)"
        return 0
    fi

    if [[ "${DRY_RUN}" == "true" ]]; then
        log_info "[DRY-RUN] Would prompt for confirmation"
        return 0
    fi

    echo ""
    echo "=========================================="
    echo "WARNING: Database Restore Operation"
    echo "=========================================="
    echo ""
    echo "This will restore the backup to database: ${DB_NAME}"
    if [[ "${DROP_EXISTING}" == "true" ]]; then
        echo "CAUTION: --drop-existing is set - existing data WILL be dropped!"
    fi
    echo ""
    echo "Type 'yes' to proceed, or anything else to cancel:"
    read -r response

    if [[ "${response}" != "yes" ]]; then
        log_info "Restore cancelled by user"
        exit 0
    fi
}

create_pre_restore_backup() {
    if [[ "${CREATE_BACKUP}" != "true" ]]; then
        return 0
    fi

    log_info "Creating pre-restore backup of current database state"

    if [[ "${DRY_RUN}" == "true" ]]; then
        log_info "[DRY-RUN] Would create pre-restore backup"
        return 0
    fi

    local backup_script="${SCRIPT_DIR}/backup-db.sh"
    if [[ -x "${backup_script}" ]]; then
        "${backup_script}" --verbose || {
            log_error "Pre-restore backup failed"
            exit 1
        }
        log_info "Pre-restore backup completed"
    else
        log_warn "Backup script not found or not executable: ${backup_script}"
    fi
}

# =============================================================================
# Restore Execution
# =============================================================================
execute_restore() {
    log_info "Starting database restore"

    if [[ "${DRY_RUN}" == "true" ]]; then
        log_info "[DRY-RUN] Would restore from: ${BACKUP_FILE_PATH}"
        log_info "[DRY-RUN] Target database: ${DB_NAME}"
        log_info "[DRY-RUN] Method: ${RESTORE_METHOD}"
        log_info "[DRY-RUN] Drop existing: ${DROP_EXISTING}"
        return 0
    fi

    local restore_cmd
    local drop_cmd=""

    if [[ "${DROP_EXISTING}" == "true" ]]; then
        log_warn "Dropping existing database objects"
        if [[ "${RESTORE_METHOD}" == "docker" ]]; then
            drop_cmd="docker exec -i ${DOCKER_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'"
        else
            drop_cmd="PGPASSWORD='${DB_PASS}' psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'"
        fi

        log_debug "Drop command: ${drop_cmd//${DB_PASS}/***}"
        if ! eval "${drop_cmd}"; then
            log_error "Failed to drop existing schema"
            exit 1
        fi
        log_info "Existing schema dropped"
    fi

    # Build restore command
    if [[ "${RESTORE_METHOD}" == "docker" ]]; then
        restore_cmd="zcat '${BACKUP_FILE_PATH}' | docker exec -i ${DOCKER_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME}"
    else
        restore_cmd="zcat '${BACKUP_FILE_PATH}' | PGPASSWORD='${DB_PASS}' psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME}"
    fi

    log_debug "Restore command: ${restore_cmd//${DB_PASS}/***}"
    log_info "Restoring database (this may take a while)..."

    local start_time
    start_time=$(date +%s)

    if ! eval "${restore_cmd}" 2>&1; then
        log_error "Restore command failed"
        exit 1
    fi

    local end_time duration
    end_time=$(date +%s)
    duration=$((end_time - start_time))

    log_info "Restore completed in ${duration} seconds"
}

verify_restore() {
    log_info "Verifying restore"

    if [[ "${DRY_RUN}" == "true" ]]; then
        log_info "[DRY-RUN] Would verify restored database"
        return 0
    fi

    local count_cmd
    if [[ "${RESTORE_METHOD}" == "docker" ]]; then
        count_cmd="docker exec ${DOCKER_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -t -c \"SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';\""
    else
        count_cmd="PGPASSWORD='${DB_PASS}' psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -t -c \"SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';\""
    fi

    local table_count
    table_count=$(eval "${count_cmd}" 2>/dev/null | tr -d ' ')

    if [[ -z "${table_count}" || "${table_count}" == "0" ]]; then
        log_warn "No tables found after restore - this may indicate a problem"
    else
        log_info "Restore verification: ${table_count} tables in database"
    fi
}

# =============================================================================
# Main Entry Point
# =============================================================================
main() {
    parse_args "$@"

    log_info "=========================================="
    log_info "Police Scanner Database Restore"
    log_info "=========================================="

    load_credentials
    resolve_backup_file
    verify_backup_file
    detect_restore_method
    show_target_info
    confirm_restore
    create_pre_restore_backup
    execute_restore
    verify_restore

    log_info "=========================================="
    log_info "Restore completed successfully"
    log_info "=========================================="
}

main "$@"
