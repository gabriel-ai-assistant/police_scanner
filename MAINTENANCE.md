# Police Scanner - Maintenance Guide

This document covers disk space management and routine maintenance procedures.

## Disk Space Safeguards

### Log Rotation (Automatic)

All Docker services have log rotation configured in `docker-compose.yml`:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "50m"
    max-file: "3"
```

This limits each service to 3 log files of 50MB each (150MB max per service).

**Services covered:**
- redis, meilisearch, signal-api
- app_scheduler, app_transcription, app_api
- frontend, flower, redisinsight

### Signal API tmpfs Mount

The `signal-api` service uses a tmpfs mount for `/tmp` to prevent native library extraction from consuming disk:

```yaml
tmpfs:
  - /tmp:size=500M
```

This stores temporary files in memory (500MB limit) instead of the container layer.

## Maintenance Script

### Location
```
/opt/policescanner/scripts/disk-cleanup.sh
```

### What It Does
1. **Truncates oversized container logs** - Safety valve for logs exceeding 100MB
2. **Cleans orphaned libsignal files** - Removes accumulated native libraries from signal-api
3. **Reports disk usage** - Shows filesystem, Docker, and container log sizes

### Manual Execution
```bash
# Basic cleanup with disk report
./scripts/disk-cleanup.sh

# Include Docker system prune (removes unused images/volumes)
./scripts/disk-cleanup.sh --prune

# Show help
./scripts/disk-cleanup.sh --help
```

### Automated Cleanup (Cron)

Set up weekly cleanup at 3 AM on Sundays:

```bash
# Edit crontab
crontab -e

# Add this line:
0 3 * * 0 /opt/policescanner/scripts/disk-cleanup.sh >> /var/log/scanner-cleanup.log 2>&1
```

## Manual Cleanup Procedures

### View Container Log Sizes
```bash
docker ps -q | xargs -I {} docker inspect --format='{{.Name}}: {{.LogPath}}' {} | while read line; do
  name=$(echo "$line" | cut -d: -f1)
  path=$(echo "$line" | cut -d: -f2)
  size=$(du -h "$path" 2>/dev/null | cut -f1)
  echo "$name: $size"
done
```

### Truncate a Specific Container Log
```bash
# Find log path
docker inspect --format='{{.LogPath}}' scanner-flower

# Truncate (requires sudo)
sudo truncate -s 0 /var/lib/docker/containers/<container-id>/<container-id>-json.log
```

### Docker System Cleanup
```bash
# Remove unused containers, networks, images
docker system prune -f

# Include unused volumes (caution: removes data!)
docker system prune -f --volumes

# Show Docker disk usage
docker system df
```

### Clean Docker Build Cache
```bash
docker builder prune -f
```

## Monitoring Recommendations

### Disk Space Alerts

Set up monitoring for:
- Root filesystem usage > 80%
- Docker storage usage > 70%
- Individual container log > 100MB

### Log Monitoring

Check for rapidly growing logs (may indicate issues):
```bash
# Watch log growth over 60 seconds
watch -n 60 'docker ps -q | xargs -I {} docker inspect --format="{{.Name}}" {} | while read name; do
  path=$(docker inspect --format="{{.LogPath}}" $name)
  du -h "$path" 2>/dev/null | cut -f1 | xargs -I {} echo "$name: {}"
done'
```

## Troubleshooting

### Disk Full Recovery

If the disk fills up:

1. **Emergency log truncation:**
   ```bash
   sudo ./scripts/disk-cleanup.sh
   ```

2. **Stop non-essential services:**
   ```bash
   docker compose stop flower redisinsight
   ```

3. **Clear Docker build cache:**
   ```bash
   docker builder prune -af
   ```

4. **Remove old images:**
   ```bash
   docker image prune -af
   ```

### Signal API /tmp Issues

If signal-api fails due to /tmp issues:

1. Check tmpfs usage:
   ```bash
   docker exec scanner-signal-api df -h /tmp
   ```

2. Clear /tmp manually:
   ```bash
   docker exec scanner-signal-api rm -rf /tmp/*
   ```

3. Restart the container:
   ```bash
   docker compose restart signal-api
   ```
