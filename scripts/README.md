# Police Scanner PostgreSQL Backup System

Production-ready database backup system with GFS (Grandfather-Father-Son) rotation for the Police Scanner application.

## Overview

This backup system provides:

- **Automated daily backups** via systemd timer (2:00 AM)
- **GFS rotation**: daily (14), weekly (12), monthly (forever)
- **Multiple backup methods**: Docker container or direct pg_dump
- **Integrity verification**: gzip checks, table counting, size validation
- **Safe restore**: confirmation prompts, dry-run mode, pre-restore backup option
- **Optional monitoring**: Prometheus metrics, webhook alerting

## Quick Start

### Installation

```bash
# Install the backup system
sudo /opt/policescanner/scripts/install-backup.sh

# Run first backup manually
/opt/policescanner/scripts/backup-db.sh --verbose

# Verify backup was created
ls -la /opt/policescanner/backups/db/daily/
```

### Manual Backup

```bash
# Standard backup
/opt/policescanner/scripts/backup-db.sh

# Verbose output
/opt/policescanner/scripts/backup-db.sh --verbose

# Preview without executing
/opt/policescanner/scripts/backup-db.sh --dry-run

# Force Docker method
/opt/policescanner/scripts/backup-db.sh --force-method=docker
```

### Restore

```bash
# Preview restore from latest backup
/opt/policescanner/scripts/restore-db.sh --dry-run latest

# Restore from latest backup
/opt/policescanner/scripts/restore-db.sh latest

# Restore specific backup
/opt/policescanner/scripts/restore-db.sh /opt/policescanner/backups/db/daily/policescanner_daily_2024-01-15_020000.sql.gz

# Restore with pre-backup of current state
/opt/policescanner/scripts/restore-db.sh --create-backup latest

# Restore to different database
/opt/policescanner/scripts/restore-db.sh --target-db=scanner_test latest
```

## Files

| File | Purpose |
|------|---------|
| `backup-config.sh` | Configuration variables (retention, paths, etc.) |
| `backup-db.sh` | Main backup script |
| `restore-db.sh` | Database restore script |
| `install-backup.sh` | Systemd installation script |
| `README.md` | This documentation |

## Directory Structure

```
/opt/policescanner/
├── scripts/
│   ├── backup-config.sh
│   ├── backup-db.sh
│   ├── restore-db.sh
│   ├── install-backup.sh
│   └── README.md
├── backups/
│   └── db/
│       ├── daily/           # 14 days retention
│       ├── weekly/          # 12 weeks retention
│       ├── monthly/         # Forever
│       └── latest.sql.gz    # Symlink to most recent
└── .env                     # Database credentials
```

If `/mnt/backups` is mounted and writable, backups are stored there instead:
```
/mnt/backups/policescanner/db/
├── daily/
├── weekly/
├── monthly/
└── latest.sql.gz
```

## Configuration

Edit `/opt/policescanner/scripts/backup-config.sh` to customize:

```bash
# Retention policy
RETAIN_DAILY=14      # Keep 14 daily backups
RETAIN_WEEKLY=12     # Keep 12 weekly backups
RETAIN_MONTHLY=0     # Keep monthly forever (0 = no limit)

# Backup settings
BACKUP_COMPRESSION_LEVEL=9   # gzip level 1-9
MIN_BACKUP_SIZE_KB=1         # Minimum valid backup size
REQUIRED_TABLE_COUNT=5       # Expected minimum tables

# Disk space
MIN_FREE_SPACE_MB=500        # Required free space

# Docker container name
DOCKER_CONTAINER="scanner-postgres"
```

## GFS Rotation Schedule

| Type | Created | Retention |
|------|---------|-----------|
| Daily | Every backup | 14 days |
| Weekly | Sundays | 12 weeks |
| Monthly | 1st of month | Forever |

**Example schedule for January:**
- Jan 1: daily + weekly + monthly
- Jan 2-6: daily only
- Jan 7: daily + weekly
- Jan 8-13: daily only
- Jan 14: daily + weekly
- ... and so on

## Systemd Timer

The backup runs automatically at 2:00 AM daily via systemd timer.

```bash
# Check timer status
systemctl status policescanner-backup.timer

# List all timers
systemctl list-timers | grep policescanner

# View next scheduled run
systemctl list-timers policescanner-backup.timer

# Manually trigger backup
systemctl start policescanner-backup.service

# View backup logs
journalctl -u policescanner-backup.service -f

# Disable automatic backups
systemctl stop policescanner-backup.timer
systemctl disable policescanner-backup.timer
```

## Backup Methods

The script automatically detects the best backup method:

### Docker Method (Preferred)
Used when the `scanner-postgres` container is running:
```bash
docker exec scanner-postgres pg_dump -U scan scanner | gzip -9
```

### Direct Method
Used when pg_dump is available locally:
```bash
PGPASSWORD="..." pg_dump -h hostname -U scan scanner | gzip -9
```

Force a specific method:
```bash
/opt/policescanner/scripts/backup-db.sh --force-method=docker
/opt/policescanner/scripts/backup-db.sh --force-method=direct
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Missing .env file |
| 2 | Missing credentials |
| 3 | No backup method available |
| 4 | Backup destination not mounted/writable |
| 5 | Insufficient disk space |
| 6 | Backup too small (likely empty) |
| 7 | Gzip integrity failure |
| 8 | Database connection timeout |
| 9 | Lock acquisition failure |

## Restore Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview without executing |
| `--verbose` | Detailed output |
| `--force-method=X` | Force docker or direct method |
| `--drop-existing` | Drop existing schema before restore |
| `--no-confirm` | Skip confirmation prompt (dangerous) |
| `--create-backup` | Backup current state first |
| `--target-db=NAME` | Restore to different database |

## Troubleshooting

### Backup fails with "No backup method available"

```bash
# Check if Docker container is running
docker ps | grep scanner-postgres

# Or install pg_dump locally
apt-get install postgresql-client
```

### Backup fails with "Insufficient disk space"

```bash
# Check available space
df -h /opt/policescanner/backups

# Prune old backups manually
find /opt/policescanner/backups/db/daily -name "*.sql.gz" -mtime +14 -delete
```

### Backup fails with "Lock acquisition failure"

Another backup may be running:
```bash
# Check for running backup
ps aux | grep backup-db

# Remove stale lock (if no backup is running)
rm -f /var/run/policescanner-backup.lock
```

### Restore fails with connection error

```bash
# Check database is accessible
docker exec scanner-postgres pg_isready -U scan

# Or for direct connection
PGPASSWORD="..." psql -h localhost -U scan -d scanner -c "SELECT 1"
```

### View backup logs

```bash
# Systemd logs
journalctl -u policescanner-backup.service --since "1 hour ago"

# Log file
tail -100 /var/log/policescanner/backup.log
```

## Optional: Prometheus Metrics

If you have node_exporter with textfile collector:

```bash
# Enable in backup-config.sh
PROMETHEUS_METRICS_DIR="/var/lib/node_exporter/textfile_collector"
PROMETHEUS_METRICS_FILE="${PROMETHEUS_METRICS_DIR}/backup_policescanner.prom"
```

Available metrics:
- `policescanner_backup_success` (0/1)
- `policescanner_backup_last_timestamp`
- `policescanner_backup_last_size_bytes`
- `policescanner_backup_duration_seconds`
- `policescanner_backup_daily_count`
- `policescanner_backup_weekly_count`
- `policescanner_backup_monthly_count`

## Optional: Webhook Alerting

Set in `.env` to receive alerts on failure:
```bash
BACKUP_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
```

Payload format:
```json
{
  "status": "failed",
  "error": "error message",
  "timestamp": "2024-01-15T02:00:00+00:00",
  "host": "hostname",
  "database": "scanner"
}
```

## Uninstall

```bash
sudo /opt/policescanner/scripts/install-backup.sh --uninstall
```

This removes systemd units but keeps:
- Scripts in `/opt/policescanner/scripts/`
- Existing backups

## Recovery Procedures

### Full Database Recovery

1. Stop application services:
   ```bash
   docker compose stop scanner-api app-scheduler scanner-transcription
   ```

2. Restore database:
   ```bash
   /opt/policescanner/scripts/restore-db.sh --drop-existing latest
   ```

3. Start services:
   ```bash
   docker compose start scanner-api app-scheduler scanner-transcription
   ```

### Point-in-Time Recovery

1. List available backups:
   ```bash
   ls -la /opt/policescanner/backups/db/daily/
   ls -la /opt/policescanner/backups/db/weekly/
   ls -la /opt/policescanner/backups/db/monthly/
   ```

2. Restore specific backup:
   ```bash
   /opt/policescanner/scripts/restore-db.sh --create-backup /path/to/backup.sql.gz
   ```

### Restore to Test Database

```bash
# Create test database first
docker exec scanner-postgres psql -U scan -c "CREATE DATABASE scanner_test;"

# Restore to test database
/opt/policescanner/scripts/restore-db.sh --target-db=scanner_test latest
```
