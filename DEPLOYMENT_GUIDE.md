# Deployment Guide - Police Scanner Optimizations

## Pre-Deployment Checklist

- [ ] Database backup completed
- [ ] Current system metrics captured (baseline)
- [ ] Environment variables verified
- [ ] Docker containers status checked

---

## Step 1: Database Schema Updates

Apply the database migrations to add monitoring tables and indexes:

```bash
# Connect to PostgreSQL
psql -U $PGUSER -h $PGHOST -p $PGPORT -d $PGDATABASE -f db/init.sql
```

**What this does:**
- Creates `system_logs` table for event logging
- Creates `api_call_metrics` table for API tracking
- Adds partial index on `bcfy_playlists(sync)`
- All changes are idempotent (safe to run multiple times)

**Verification:**
```sql
-- Check tables exist
\dt system_logs
\dt api_call_metrics

-- Check index exists
\di bcfy_playlists_sync_idx
```

---

## Step 2: Verify File Changes

Confirm all optimization files are in place:

```bash
# Check new files exist
ls -la app_scheduler/db_pool.py
ls -la app_scheduler/audio_worker.py
ls -la db/monitoring_queries.sql
ls -la OPTIMIZATION_SUMMARY.md

# Check modified files
git status
```

**Expected output:** Should show:
- Modified: `app_scheduler/get_calls.py`
- Modified: `app_scheduler/scheduler.py`
- Modified: `db/init.sql`
- New: `app_scheduler/db_pool.py`
- New: `app_scheduler/audio_worker.py`
- New: `db/monitoring_queries.sql`
- New: `OPTIMIZATION_SUMMARY.md`

---

## Step 3: Environment Variables

Verify required environment variables are set in `.env`:

```bash
# Required variables
PGUSER=your_user
PGPASSWORD=your_password
PGDATABASE=your_database
PGHOST=localhost
PGPORT=5432

# Broadcastify API
BCFY_API_KEY_ID=your_key_id
BCFY_API_KEY=your_key
BCFY_APP_ID=your_app_id
BCFY_BASE_URL=https://api.bcfy.io

# MinIO/S3
MINIO_ENDPOINT=localhost:9000
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=adminadmin
MINIO_BUCKET=feeds
AUDIO_BUCKET_PATH=calls

# Timing (optional, defaults shown)
COLLECT_INTERVAL_SEC=10
AUDIO_WORKER_INTERVAL_SEC=5
AUDIO_WORKER_BATCH_SIZE=20

# Audio processing (optional)
TEMP_AUDIO_DIR=/app/shared_bcfy/tmp
AUDIO_SAMPLE_RATE=16000
AUDIO_TARGET_DB=-20
```

---

## Step 4: Restart Services

### Option A: Using Docker Compose (Recommended)

```bash
# Stop services
docker-compose down

# Rebuild (if using custom images)
docker-compose build app_scheduler

# Start services
docker-compose up -d

# Watch logs
docker-compose logs -f app_scheduler
```

### Option B: Local Development

```bash
# Kill existing scheduler process
pkill -f scheduler.py

# Start scheduler
cd app_scheduler
python scheduler.py
```

---

## Step 5: Verify Deployment (First 5 Minutes)

### 5.1 Check Logs for Errors

```bash
# Watch scheduler logs
docker-compose logs -f app_scheduler | grep -E "ERROR|WARN|✅|❌"
```

**Expected log messages:**
```
Starting ingestion cycle
Using X cached groups from DB
Processed Y calls in Zms
Cycle done in <1000ms (Y new calls); sleeping 10s
Processing X pending audio files...
✓ Processed call_uid
```

### 5.2 Verify Database Activity

```sql
-- Check ingestion cycles are logging
SELECT
    timestamp,
    message,
    duration_ms
FROM system_logs
WHERE component = 'ingestion'
  AND event_type = 'cycle_complete'
ORDER BY timestamp DESC
LIMIT 5;

-- Check API calls are being tracked
SELECT
    timestamp,
    endpoint,
    duration_ms,
    status_code
FROM api_call_metrics
ORDER BY timestamp DESC
LIMIT 10;

-- Check audio processing status
SELECT
    processed,
    COUNT(*) as count
FROM bcfy_calls_raw
GROUP BY processed;
```

---

## Step 6: Monitor Performance (First Hour)

### 6.1 API Call Rate

**Goal:** <10 API calls per hour (down from ~360/hour)

```sql
-- Check API call rate
SELECT
    COUNT(*) as api_calls_last_hour,
    CASE
        WHEN COUNT(*) < 10 THEN '✅ Excellent'
        WHEN COUNT(*) < 20 THEN '⚠️ Good'
        ELSE '❌ Too high - investigate'
    END as status
FROM api_call_metrics
WHERE timestamp > NOW() - INTERVAL '1 hour';
```

### 6.2 Duplicate Detection

**Goal:** 0 duplicate calls

```sql
-- Check for duplicates
SELECT
    COUNT(*) as duplicate_count,
    CASE
        WHEN COUNT(*) = 0 THEN '✅ No duplicates'
        ELSE '❌ Found duplicates - check last_seen logic'
    END as status
FROM (
    SELECT call_uid
    FROM bcfy_calls_raw
    WHERE fetched_at > NOW() - INTERVAL '1 hour'
    GROUP BY call_uid
    HAVING COUNT(*) > 1
) dups;
```

### 6.3 Last_Seen Updates

**Goal:** Timestamps within last 15 minutes

```sql
-- Check last_seen freshness
SELECT
    uuid,
    name,
    TO_TIMESTAMP(last_seen) as last_seen_time,
    NOW() - TO_TIMESTAMP(last_seen) as staleness,
    CASE
        WHEN NOW() - TO_TIMESTAMP(last_seen) < INTERVAL '15 minutes' THEN '✅ Fresh'
        WHEN NOW() - TO_TIMESTAMP(last_seen) < INTERVAL '1 hour' THEN '⚠️ Stale'
        ELSE '❌ Very stale - investigate'
    END as status
FROM bcfy_playlists
WHERE sync = TRUE;
```

### 6.4 Audio Processing Backlog

**Goal:** <100 unprocessed calls

```sql
-- Check audio backlog
SELECT
    COUNT(*) as pending_audio,
    CASE
        WHEN COUNT(*) < 100 THEN '✅ Near real-time'
        WHEN COUNT(*) < 500 THEN '⚠️ Growing backlog'
        ELSE '❌ Large backlog - check worker'
    END as status
FROM bcfy_calls_raw
WHERE processed = FALSE AND error IS NULL;
```

### 6.5 Cycle Performance

**Goal:** <5000ms average cycle time

```sql
-- Check cycle performance
SELECT
    COUNT(*) as cycle_count,
    ROUND(AVG(duration_ms)) as avg_ms,
    MAX(duration_ms) as max_ms,
    CASE
        WHEN AVG(duration_ms) < 5000 THEN '✅ Fast'
        WHEN AVG(duration_ms) < 10000 THEN '⚠️ OK'
        ELSE '❌ Slow - investigate'
    END as status
FROM system_logs
WHERE component = 'ingestion'
  AND event_type = 'cycle_complete'
  AND timestamp > NOW() - INTERVAL '1 hour';
```

---

## Step 7: Long-Term Monitoring Setup

### 7.1 Create Monitoring Dashboard

Use queries from [db/monitoring_queries.sql](db/monitoring_queries.sql):

```bash
# Copy monitoring queries for easy access
cp db/monitoring_queries.sql ~/police_scanner_monitoring.sql
```

### 7.2 Set Up Alerts (Optional)

Create a monitoring script that runs every hour:

```bash
# Create monitoring script
cat > scripts/check_health.sh << 'EOF'
#!/bin/bash
# Police Scanner Health Check

PGUSER="${PGUSER}"
PGDATABASE="${PGDATABASE}"

echo "=== Police Scanner Health Check $(date) ==="

# Check API call rate
API_CALLS=$(psql -U $PGUSER -d $PGDATABASE -t -c "
    SELECT COUNT(*) FROM api_call_metrics
    WHERE timestamp > NOW() - INTERVAL '1 hour';
")

if [ $API_CALLS -gt 20 ]; then
    echo "❌ ALERT: High API call rate ($API_CALLS/hour)"
fi

# Check audio backlog
BACKLOG=$(psql -U $PGUSER -d $PGDATABASE -t -c "
    SELECT COUNT(*) FROM bcfy_calls_raw
    WHERE processed = FALSE AND error IS NULL;
")

if [ $BACKLOG -gt 1000 ]; then
    echo "❌ ALERT: Large audio backlog ($BACKLOG calls)"
fi

# Check cycle time
AVG_CYCLE=$(psql -U $PGUSER -d $PGDATABASE -t -c "
    SELECT ROUND(AVG(duration_ms)) FROM system_logs
    WHERE component = 'ingestion'
      AND event_type = 'cycle_complete'
      AND timestamp > NOW() - INTERVAL '1 hour';
")

if [ $AVG_CYCLE -gt 5000 ]; then
    echo "❌ ALERT: Slow cycles (${AVG_CYCLE}ms avg)"
fi

echo "✅ Health check complete"
EOF

chmod +x scripts/check_health.sh
```

---

## Rollback Procedure (If Needed)

If you encounter critical issues:

### Rollback Code Changes

```bash
# Option 1: Git revert (if committed)
git revert HEAD
docker-compose restart app_scheduler

# Option 2: Manual restore from backup
git checkout <previous-commit-hash> app_scheduler/
docker-compose restart app_scheduler
```

### Rollback Database (Optional)

Database changes are backwards compatible and can remain. If needed:

```sql
-- Remove monitoring tables (optional)
DROP TABLE IF EXISTS api_call_metrics;
DROP TABLE IF EXISTS system_logs;

-- Remove index (optional)
DROP INDEX IF EXISTS bcfy_playlists_sync_idx;
```

---

## Success Criteria

After 24 hours of operation, verify:

- ✅ API call rate: <10/hour (90%+ reduction)
- ✅ Duplicate calls: 0%
- ✅ Audio processing latency: <1 minute
- ✅ Ingestion cycle time: <1 second average
- ✅ No increase in error rate
- ✅ `last_seen` timestamps updating every 10-15 seconds

---

## Troubleshooting

### Issue: High API Call Rate (>20/hour)

**Check:**
```sql
-- Which endpoints are being called?
SELECT
    regexp_replace(endpoint, '/[0-9a-f-]+', '/{id}', 'g') as pattern,
    COUNT(*) as calls
FROM api_call_metrics
WHERE timestamp > NOW() - INTERVAL '1 hour'
GROUP BY pattern
ORDER BY calls DESC;
```

**Possible causes:**
- `last_seen` not updating (check logs)
- `groups_json` not cached (check database)
- JWT token cache not working (check imports)

### Issue: Audio Backlog Growing

**Check:**
```sql
-- Check for errors
SELECT error, COUNT(*)
FROM bcfy_calls_raw
WHERE error IS NOT NULL
GROUP BY error;
```

**Possible causes:**
- Audio worker not running (check scheduler logs)
- FFmpeg failures (check error column)
- MinIO connection issues (check network)

### Issue: Slow Cycle Times

**Check:**
```sql
-- Find slow cycles
SELECT timestamp, duration_ms, metadata
FROM system_logs
WHERE component = 'ingestion'
  AND event_type = 'cycle_complete'
  AND duration_ms > 5000
ORDER BY duration_ms DESC
LIMIT 10;
```

**Possible causes:**
- Database connection pool exhausted
- Network latency to Broadcastify
- Large number of new calls

---

## Post-Deployment Tasks

After successful deployment:

1. **Document baseline metrics:**
   ```bash
   # Save baseline report
   psql -U $PGUSER -d $PGDATABASE -f db/monitoring_queries.sql > reports/baseline_$(date +%Y%m%d).txt
   ```

2. **Schedule regular monitoring:**
   ```bash
   # Add to crontab
   0 * * * * /path/to/scripts/check_health.sh >> /var/log/police_scanner_health.log
   ```

3. **Update documentation:**
   - Mark optimization plan as complete
   - Document any custom configuration changes
   - Update team runbook with new monitoring queries

---

## Contact

For issues or questions about this deployment:
- Review: [OPTIMIZATION_SUMMARY.md](OPTIMIZATION_SUMMARY.md)
- Monitoring: [db/monitoring_queries.sql](db/monitoring_queries.sql)
- Plan: [.claude/plans/magical-moseying-octopus.md](.claude/plans/magical-moseying-octopus.md)
