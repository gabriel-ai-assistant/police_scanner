#!/bin/bash
#
# disk-cleanup.sh - Disk space maintenance for Police Scanner
#
# This script performs safe disk cleanup operations:
# - Truncates oversized container logs (safety valve beyond Docker rotation)
# - Cleans orphaned libsignal* files from signal-api container
# - Reports current disk usage
#
# Safe to run via cron (idempotent)
# Recommended: 0 3 * * 0 /opt/policescanner/scripts/disk-cleanup.sh >> /var/log/scanner-cleanup.log 2>&1
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_SIZE_THRESHOLD_MB=100
SIGNAL_CONTAINER="scanner-signal-api"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Colors for output (disabled if not interactive)
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

log_info() {
    echo -e "[$TIMESTAMP] ${GREEN}INFO${NC}: $1"
}

log_warn() {
    echo -e "[$TIMESTAMP] ${YELLOW}WARN${NC}: $1"
}

log_error() {
    echo -e "[$TIMESTAMP] ${RED}ERROR${NC}: $1"
}

# Function to get Docker container log paths
get_container_log_paths() {
    docker ps -q 2>/dev/null | while read -r container_id; do
        docker inspect --format='{{.LogPath}}' "$container_id" 2>/dev/null || true
    done | grep -v '^$' | sort -u
}

# Function to truncate oversized container logs
truncate_oversized_logs() {
    log_info "Checking for oversized container logs (threshold: ${LOG_SIZE_THRESHOLD_MB}MB)..."

    local truncated_count=0
    local threshold_bytes=$((LOG_SIZE_THRESHOLD_MB * 1024 * 1024))

    for log_path in $(get_container_log_paths); do
        if [[ -f "$log_path" ]]; then
            local size
            size=$(stat -c%s "$log_path" 2>/dev/null || echo 0)

            if [[ $size -gt $threshold_bytes ]]; then
                local size_mb=$((size / 1024 / 1024))
                log_warn "Truncating $log_path (${size_mb}MB > ${LOG_SIZE_THRESHOLD_MB}MB threshold)"

                # Truncate the log file (Docker will continue appending)
                if truncate -s 0 "$log_path" 2>/dev/null; then
                    truncated_count=$((truncated_count + 1))
                else
                    log_error "Failed to truncate $log_path (may need sudo)"
                fi
            fi
        fi
    done

    if [[ $truncated_count -eq 0 ]]; then
        log_info "No oversized logs found"
    else
        log_info "Truncated $truncated_count log file(s)"
    fi
}

# Function to clean orphaned libsignal files from signal-api container
clean_signal_tmp() {
    log_info "Checking for orphaned libsignal files in $SIGNAL_CONTAINER..."

    # Check if container exists and is running
    if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${SIGNAL_CONTAINER}$"; then
        log_warn "Container $SIGNAL_CONTAINER is not running, skipping libsignal cleanup"
        return 0
    fi

    # Find and remove orphaned libsignal* files in /tmp
    # These are native libraries extracted by signal-cli that can accumulate
    local cleanup_output
    cleanup_output=$(docker exec "$SIGNAL_CONTAINER" sh -c '
        count=0
        for f in /tmp/libsignal* 2>/dev/null; do
            if [ -e "$f" ]; then
                rm -f "$f" 2>/dev/null && count=$((count + 1))
            fi
        done
        echo $count
    ' 2>/dev/null || echo "0")

    if [[ "$cleanup_output" == "0" ]]; then
        log_info "No orphaned libsignal files found"
    else
        log_info "Cleaned $cleanup_output orphaned libsignal file(s)"
    fi
}

# Function to report disk usage
report_disk_usage() {
    log_info "Current disk usage:"
    echo ""

    # Overall disk usage
    echo "=== Filesystem Usage ==="
    df -h / | tail -n 1 | awk '{printf "  Root filesystem: %s used of %s (%s)\n", $3, $2, $5}'

    # Docker disk usage
    if command -v docker &>/dev/null; then
        echo ""
        echo "=== Docker Disk Usage ==="
        docker system df 2>/dev/null | tail -n +2 | while read -r line; do
            echo "  $line"
        done
    fi

    # Container log sizes
    echo ""
    echo "=== Container Log Sizes ==="
    for log_path in $(get_container_log_paths); do
        if [[ -f "$log_path" ]]; then
            local container_name
            container_name=$(docker ps --format '{{.Names}}' --filter "id=$(basename "$(dirname "$log_path")")" 2>/dev/null | head -1)
            if [[ -z "$container_name" ]]; then
                container_name="unknown"
            fi
            local size
            size=$(du -h "$log_path" 2>/dev/null | cut -f1)
            echo "  $container_name: $size"
        fi
    done

    # Project directory size
    echo ""
    echo "=== Project Directory ==="
    du -sh "$PROJECT_DIR" 2>/dev/null | awk '{printf "  %s: %s\n", $2, $1}'

    # Data directory sizes if present
    if [[ -d "$PROJECT_DIR/data" ]]; then
        echo ""
        echo "=== Data Directories ==="
        du -sh "$PROJECT_DIR/data"/* 2>/dev/null | while read -r size path; do
            echo "  $(basename "$path"): $size"
        done
    fi

    echo ""
}

# Function to run Docker system prune (optional, requires --prune flag)
docker_prune() {
    log_info "Running Docker system prune..."
    docker system prune -f --volumes 2>/dev/null || log_warn "Docker prune failed or not available"
}

# Main
main() {
    echo "========================================"
    echo "Police Scanner Disk Cleanup"
    echo "Started: $TIMESTAMP"
    echo "========================================"
    echo ""

    # Parse arguments
    local do_prune=false
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --prune)
                do_prune=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --prune    Also run docker system prune (removes unused images/volumes)"
                echo "  --help     Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Run cleanup tasks
    truncate_oversized_logs
    echo ""

    clean_signal_tmp
    echo ""

    if [[ "$do_prune" == true ]]; then
        docker_prune
        echo ""
    fi

    report_disk_usage

    echo "========================================"
    echo "Cleanup completed: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================"
}

main "$@"
