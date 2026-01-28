#!/usr/bin/env bash
# =============================================================================
# Police Scanner Backup System Installation Script
# =============================================================================
# Installs the backup scripts, creates directories, and sets up systemd timers.
#
# Usage: sudo ./install-backup.sh [--uninstall]
#
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="/opt/policescanner"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# =============================================================================
# Utility Functions
# =============================================================================
log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# =============================================================================
# Uninstall Function
# =============================================================================
uninstall() {
    log_info "Uninstalling Police Scanner backup system..."

    # Stop and disable timer
    if systemctl is-active --quiet policescanner-backup.timer 2>/dev/null; then
        systemctl stop policescanner-backup.timer
        log_info "Stopped backup timer"
    fi

    if systemctl is-enabled --quiet policescanner-backup.timer 2>/dev/null; then
        systemctl disable policescanner-backup.timer
        log_info "Disabled backup timer"
    fi

    # Remove systemd units
    rm -f /etc/systemd/system/policescanner-backup.service
    rm -f /etc/systemd/system/policescanner-backup.timer
    systemctl daemon-reload

    log_info "Removed systemd units"
    log_info "Uninstall complete"
    log_warn "Note: Backup scripts in ${SCRIPT_DIR} were NOT removed"
    log_warn "Note: Existing backups were NOT removed"

    exit 0
}

# =============================================================================
# Installation Functions
# =============================================================================
create_directories() {
    log_info "Creating directories..."

    # Log directory
    mkdir -p /var/log/policescanner
    chmod 755 /var/log/policescanner
    log_info "  Created /var/log/policescanner"

    # Local backup directory (fallback if /mnt/backups not available)
    mkdir -p "${PROJECT_DIR}/backups/db/daily"
    mkdir -p "${PROJECT_DIR}/backups/db/weekly"
    mkdir -p "${PROJECT_DIR}/backups/db/monthly"
    chmod -R 750 "${PROJECT_DIR}/backups"
    log_info "  Created ${PROJECT_DIR}/backups/db/{daily,weekly,monthly}"

    # External backup directory (if mount exists)
    if [[ -d /mnt/backups ]] && [[ -w /mnt/backups ]]; then
        mkdir -p /mnt/backups/policescanner/db/daily
        mkdir -p /mnt/backups/policescanner/db/weekly
        mkdir -p /mnt/backups/policescanner/db/monthly
        chmod -R 750 /mnt/backups/policescanner
        log_info "  Created /mnt/backups/policescanner/db/{daily,weekly,monthly}"
    else
        log_warn "  /mnt/backups not available - using local fallback"
    fi

    # Lock file directory
    mkdir -p /var/run
}

set_permissions() {
    log_info "Setting script permissions..."

    chmod 750 "${SCRIPT_DIR}/backup-db.sh"
    chmod 750 "${SCRIPT_DIR}/restore-db.sh"
    chmod 640 "${SCRIPT_DIR}/backup-config.sh"
    chmod 750 "${SCRIPT_DIR}/install-backup.sh"

    log_info "  Scripts set to 750/640"
}

install_systemd_units() {
    log_info "Installing systemd units..."

    # Create service unit
    cat > /etc/systemd/system/policescanner-backup.service << 'EOF'
[Unit]
Description=Police Scanner PostgreSQL Database Backup
Documentation=file:///opt/policescanner/scripts/README.md
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/opt/policescanner/scripts/backup-db.sh
User=root
Group=root

# Timeouts
TimeoutStartSec=3600

# Security hardening
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
NoNewPrivileges=true

# Required paths
ReadWritePaths=/mnt/backups /var/log/policescanner /var/run /opt/policescanner/backups

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=policescanner-backup

[Install]
WantedBy=multi-user.target
EOF

    log_info "  Created policescanner-backup.service"

    # Create timer unit
    cat > /etc/systemd/system/policescanner-backup.timer << 'EOF'
[Unit]
Description=Daily Police Scanner Database Backup Timer
Documentation=file:///opt/policescanner/scripts/README.md

[Timer]
# Run daily at 2:00 AM with up to 5 minutes random delay
OnCalendar=*-*-* 02:00:00
RandomizedDelaySec=300

# Catch up on missed runs (e.g., if system was powered off)
Persistent=true

# Nice accuracy for non-critical backup
AccuracySec=1min

[Install]
WantedBy=timers.target
EOF

    log_info "  Created policescanner-backup.timer"

    # Reload systemd
    systemctl daemon-reload
    log_info "  Reloaded systemd daemon"
}

enable_timer() {
    log_info "Enabling backup timer..."

    systemctl enable policescanner-backup.timer
    systemctl start policescanner-backup.timer

    log_info "  Timer enabled and started"
}

verify_installation() {
    log_info "Verifying installation..."

    local errors=0

    # Check scripts exist and are executable
    for script in backup-db.sh restore-db.sh backup-config.sh; do
        if [[ ! -f "${SCRIPT_DIR}/${script}" ]]; then
            log_error "  Missing: ${script}"
            ((errors++))
        fi
    done

    # Check systemd units
    if ! systemctl list-unit-files | grep -q policescanner-backup.service; then
        log_error "  Service unit not installed"
        ((errors++))
    fi

    if ! systemctl list-unit-files | grep -q policescanner-backup.timer; then
        log_error "  Timer unit not installed"
        ((errors++))
    fi

    # Check timer is active
    if ! systemctl is-active --quiet policescanner-backup.timer; then
        log_warn "  Timer is not running (this may be expected)"
    fi

    if [[ ${errors} -gt 0 ]]; then
        log_error "Installation verification failed with ${errors} error(s)"
        return 1
    fi

    log_info "  All checks passed"
    return 0
}

run_test_backup() {
    log_info "Running test backup (dry-run)..."

    if "${SCRIPT_DIR}/backup-db.sh" --dry-run --verbose; then
        log_info "  Dry-run completed successfully"
    else
        log_warn "  Dry-run failed - check configuration"
    fi
}

print_summary() {
    echo ""
    echo "=========================================="
    echo "Installation Complete"
    echo "=========================================="
    echo ""
    echo "Scripts installed:"
    echo "  ${SCRIPT_DIR}/backup-db.sh"
    echo "  ${SCRIPT_DIR}/restore-db.sh"
    echo "  ${SCRIPT_DIR}/backup-config.sh"
    echo ""
    echo "Systemd units:"
    echo "  policescanner-backup.service"
    echo "  policescanner-backup.timer (runs daily at 2:00 AM)"
    echo ""
    echo "Useful commands:"
    echo "  # Run backup manually"
    echo "  ${SCRIPT_DIR}/backup-db.sh --verbose"
    echo ""
    echo "  # Check timer status"
    echo "  systemctl status policescanner-backup.timer"
    echo "  systemctl list-timers | grep policescanner"
    echo ""
    echo "  # View backup logs"
    echo "  journalctl -u policescanner-backup.service"
    echo "  tail -f /var/log/policescanner/backup.log"
    echo ""
    echo "  # Restore from latest backup"
    echo "  ${SCRIPT_DIR}/restore-db.sh --dry-run latest"
    echo ""
    echo "  # Uninstall"
    echo "  sudo ${SCRIPT_DIR}/install-backup.sh --uninstall"
    echo ""
}

# =============================================================================
# Main Entry Point
# =============================================================================
main() {
    echo "=========================================="
    echo "Police Scanner Backup System Installer"
    echo "=========================================="
    echo ""

    # Check for uninstall flag
    if [[ "${1:-}" == "--uninstall" ]]; then
        check_root
        uninstall
    fi

    check_root

    create_directories
    set_permissions
    install_systemd_units
    enable_timer
    verify_installation
    run_test_backup
    print_summary
}

main "$@"
