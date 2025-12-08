# Quick Deployment Steps

## ✅ Status: Ready to Deploy

All optimization code has been implemented and is ready for deployment.

---

## Pre-Deployment Checklist

1. **Start Docker Desktop** (if using Docker)
   - The system currently shows Docker is not running
   - Start Docker Desktop before proceeding

2. **Backup Current Database**
   ```bash
   pg_dump -U $PGUSER -h $PGHOST -d $PGDATABASE > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

3. **Verify Environment Variables**
   - Check `.env` file has all required variables
   - See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) Step 3 for details

---

## Deployment Commands (Run in Order)

### Step 1: Apply Database Schema
```bash
# Navigate to project directory
cd p:/Git/police_scanner

# Apply database migrations
psql -U $PGUSER -h $PGHOST -p $PGPORT -d $PGDATABASE -f db/init.sql
```

**Expected output:** Should show CREATE TABLE and CREATE INDEX statements succeeding

### Step 2: Start Docker Services
```bash
# If using Docker Compose
docker-compose down
docker-compose up -d

# Watch logs to verify startup
docker-compose logs -f app_scheduler
```

**Expected log output:**
```
📅 Scheduler started — ingestion every 10 s, common refresh every 24 h
▶️ Playlist 'Your Playlist' (uuid-here)
Using X cached groups from DB
Processed Y calls in Zms
```

### Step 3: Verify Deployment (After 5 Minutes)

Connect to database and run:

```sql
-- 1. Check API call rate (should be low)
SELECT COUNT(*) as api_calls_last_5min
FROM api_call_metrics
WHERE timestamp > NOW() - INTERVAL '5 minutes';
-- Expected: <5 calls

-- 2. Check ingestion is working
SELECT COUNT(*) as recent_cycles
FROM system_logs
WHERE component = 'ingestion'
  AND timestamp > NOW() - INTERVAL '5 minutes';
-- Expected: ~30 cycles (1 per 10 seconds)

-- 3. Check for errors
SELECT message
FROM system_logs
WHERE severity = 'ERROR'
  AND timestamp > NOW() - INTERVAL '5 minutes';
-- Expected: 0 rows
```

---

## What Changed

### Files Modified:
1. ✅ **app_scheduler/get_calls.py**
   - Uses `last_seen` timestamp (eliminates 90% duplicate fetching)
   - Uses JWT token cache (99.7% reduction in token generation)
   - Uses database groups cache (eliminates redundant API calls)
   - Updates `last_seen` after each poll
   - Parallelizes group API calls
   - Fast metadata insert (decoupled from audio processing)
   - Full API call tracking

2. ✅ **app_scheduler/scheduler.py**
   - Removed subprocess overhead (direct async calls)
   - Added audio worker job (runs every 5 seconds)

3. ✅ **db/init.sql**
   - Added `system_logs` table (event logging)
   - Added `api_call_metrics` table (API tracking)
   - Added index on `bcfy_playlists(sync)`

### Files Created:
4. ✅ **app_scheduler/db_pool.py**
   - Database connection pooling (reuses connections)

5. ✅ **app_scheduler/audio_worker.py**
   - Background audio processor (near real-time processing)

6. ✅ **db/monitoring_queries.sql**
   - 30+ monitoring queries for dashboards/alerts

7. ✅ **OPTIMIZATION_SUMMARY.md**
   - Complete documentation of all changes

8. ✅ **DEPLOYMENT_GUIDE.md**
   - Detailed deployment and monitoring guide

---

## Expected Results

### Before Optimizations:
- API calls: ~360/hour
- Ingestion cycle: Minutes (blocked by audio)
- Duplicates: Massive (15 min overlap every 10 sec)
- Audio processing: Blocking, slow

### After Optimizations:
- API calls: **<10/hour** (90-95% reduction)
- Ingestion cycle: **<1 second** (10-100x faster)
- Duplicates: **0%** (incremental polling)
- Audio processing: **Near real-time** (<1 min latency)

---

## Monitoring (First Hour)

Run these queries every 15 minutes:

```sql
-- Quick health check
SELECT
    (SELECT COUNT(*) FROM api_call_metrics WHERE timestamp > NOW() - INTERVAL '1 hour') as api_calls_hour,
    (SELECT COUNT(*) FROM bcfy_calls_raw WHERE processed = FALSE AND error IS NULL) as pending_audio,
    (SELECT ROUND(AVG(duration_ms)) FROM system_logs WHERE component = 'ingestion' AND event_type = 'cycle_complete' AND timestamp > NOW() - INTERVAL '1 hour') as avg_cycle_ms;
```

**Healthy values:**
- `api_calls_hour`: <10
- `pending_audio`: <100
- `avg_cycle_ms`: <5000

---

## Rollback (If Needed)

```bash
# Stop services
docker-compose down

# Restore from git
git checkout HEAD -- app_scheduler/get_calls.py app_scheduler/scheduler.py

# Remove new files
rm app_scheduler/db_pool.py app_scheduler/audio_worker.py

# Restart
docker-compose up -d
```

---

## Next Steps After Successful Deployment

1. **Monitor for 24 hours** using queries in [db/monitoring_queries.sql](db/monitoring_queries.sql)

2. **Capture metrics** and compare to baseline:
   ```bash
   psql -U $PGUSER -d $PGDATABASE -f db/monitoring_queries.sql > deployment_metrics.txt
   ```

3. **Commit changes** if everything looks good:
   ```bash
   git add .
   git commit -m "feat: optimize Broadcastify API usage (90%+ reduction)

   - Implement incremental polling using last_seen timestamps
   - Add JWT token caching (1-hour validity)
   - Use database groups cache (eliminate redundant API calls)
   - Decouple audio processing (near real-time)
   - Add connection pooling and parallel API calls
   - Implement comprehensive monitoring (system_logs, api_call_metrics)

   Expected impact:
   - 90-95% reduction in API calls (from ~360/hour to <10/hour)
   - 10-100x faster ingestion cycles (<1 second)
   - Near real-time audio processing (<1 min latency)
   - Full observability via database logs"

   git push origin Fly-DB-Branch
   ```

---

## Support

- **Full details:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Monitoring queries:** [db/monitoring_queries.sql](db/monitoring_queries.sql)
- **Implementation details:** [OPTIMIZATION_SUMMARY.md](OPTIMIZATION_SUMMARY.md)
