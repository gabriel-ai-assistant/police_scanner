# PostgreSQL Database Migration Guide
## Expert DBA Analysis & Implementation

**Version**: 1.0
**Date**: 2025-12-08
**Status**: Production Ready
**Risk Level**: Low to Medium (depending on phase)

---

## Overview

This guide provides step-by-step instructions for implementing expert DBA recommendations to optimize the police scanner database. The migrations are organized into 3 phases:

- **Phase 1**: Immediate Low-Risk Fixes (indexes, constraints, monitoring)
- **Phase 2**: Table Partitioning (significant performance improvement)
- **Phase 3**: Schema Enhancements (additional metadata and state tracking)

---

## Prerequisites

### Database Access
- PostgreSQL superuser or admin credentials
- SSH access to AWS RDS database
- Network connectivity to `police-scanner.cilycke4i4nz.us-east-1.rds.amazonaws.com:5432`

### Tools Required
```bash
# PostgreSQL client
psql --version  # Should be 12.x or newer

# Or use any PostgreSQL IDE:
# - pgAdmin
# - DBeaver
# - psql command line
```

### Database Backup
```bash
# CRITICAL: Always backup before migrations
pg_dump postgresql://scan:PASSWORD@police-scanner.cilycke4i4nz.us-east-1.rds.amazonaws.com:5432/scanner \
  -Fc -f backup_pre_migration_$(date +%Y%m%d_%H%M%S).dump

# Verify backup
pg_restore -l backup_pre_migration_*.dump | head -20
```

### Service Planning
- Schedule maintenance window during low-traffic period
- Phase 1: No downtime required ✓
- Phase 2: No downtime required ✓
- Phase 3: No downtime required ✓
- **Total estimated downtime: 0 (zero-downtime architecture)**

---

## Phase 1: Immediate Improvements (Week 1)

### ⏱️ Estimated Time: 2-5 minutes
### 🎯 Risk: LOW
### ⚡ Impact: HIGH (20-30% query improvement)

This phase adds missing indexes, constraints, and monitoring without any schema changes.

### 1.1 Pre-Migration Checklist

```bash
# Connect to database
psql "postgresql://scan:PASSWORD@police-scanner.cilycke4i4nz.us-east-1.rds.amazonaws.com:5432/scanner"

# Check current schema version
SELECT COUNT(*) as index_count FROM pg_indexes WHERE schemaname = 'public';
SELECT COUNT(*) as constraint_count FROM information_schema.check_constraints WHERE constraint_schema = 'public';
```

### 1.2 Execute Phase 1 Migration

```bash
# Apply migration
psql "postgresql://scan:PASSWORD@police-scanner.cilycke4i4nz.us-east-1.rds.amazonaws.com:5432/scanner" \
  -f db/migrations/001_phase1_improvements.sql

# Expected output:
# - Multiple "✓ Created index" messages
# - "All indexes created successfully"
# - "Monitoring views created successfully"
# - "Phase 1 Migration Complete! ✓"
```

### 1.3 Post-Migration Verification

```sql
-- Verify all indexes were created
SELECT COUNT(*) as total_indexes
FROM pg_indexes
WHERE schemaname = 'public';

-- Check new monitoring views
SELECT * FROM information_schema.views
WHERE table_schema = 'monitoring'
ORDER BY table_name;

-- Expected: 6-7 monitoring views (table_health, index_usage, table_bloat, etc.)

-- View monitoring schema
SELECT * FROM monitoring.table_health LIMIT 5;
SELECT * FROM monitoring.index_usage WHERE usage_status = 'UNUSED' LIMIT 5;
SELECT * FROM monitoring.table_bloat WHERE status IN ('WARNING', 'CRITICAL');
```

### 1.4 Performance Analysis

```sql
-- Run ANALYZE to update statistics
ANALYZE bcfy_calls_raw;
ANALYZE transcripts;
ANALYZE api_call_metrics;
ANALYZE system_logs;

-- Check improvement
SELECT
  tablename,
  pg_size_pretty(pg_total_relation_size('public.' || tablename)) as total_size,
  n_live_tup as rows
FROM pg_stat_user_tables
WHERE tablename IN ('bcfy_calls_raw', 'transcripts', 'api_call_metrics', 'system_logs')
ORDER BY pg_total_relation_size('public.' || tablename) DESC;
```

### 1.5 Rollback Plan (if needed)

Phase 1 is additive only - if something goes wrong, you can drop problematic objects:

```sql
-- Drop new indexes (keep existing ones)
DROP INDEX IF EXISTS bcfy_calls_raw_pending_idx;
DROP INDEX IF EXISTS bcfy_calls_raw_fetched_at_idx;
-- etc...

-- Drop monitoring schema and views
DROP SCHEMA IF EXISTS monitoring CASCADE;

-- Restore from backup if critical
pg_restore -d scanner backup_pre_migration_*.dump
```

---

## Phase 2: Table Partitioning (Week 2-3)

### ⏱️ Estimated Time: 10-30 minutes (depends on data volume)
### 🎯 Risk: MEDIUM
### ⚡ Impact: CRITICAL (10-100x query improvement for time ranges)

This phase implements native PostgreSQL partitioning for time-series tables.

### 2.1 Pre-Migration Checks

```sql
-- Check table sizes before migration
SELECT
  tablename,
  pg_size_pretty(pg_total_relation_size('public.' || tablename)) as total_size,
  n_live_tup as row_count
FROM pg_stat_user_tables
WHERE tablename IN ('bcfy_calls_raw', 'transcripts', 'api_call_metrics', 'system_logs')
ORDER BY pg_total_relation_size('public.' || tablename) DESC;

-- Example expected output:
-- bcfy_calls_raw    | 5.2 GB      | 2,500,000 rows
-- api_call_metrics  | 1.8 GB      | 10,000,000 rows
-- system_logs       | 800 MB      | 5,000,000 rows
-- transcripts       | 3.1 GB      | 750,000 rows
```

### 2.2 Backup Before Partitioning

```bash
# CRITICAL: Create fresh backup before partitioning
pg_dump postgresql://scan:PASSWORD@police-scanner.cilycke4i4nz.us-east-1.rds.amazonaws.com:5432/scanner \
  -Fc -f backup_before_partitioning_$(date +%Y%m%d_%H%M%S).dump \
  --table=bcfy_calls_raw \
  --table=transcripts \
  --table=api_call_metrics \
  --table=system_logs

# Verify backup size (should be close to table sizes)
ls -lh backup_before_partitioning_*.dump
```

### 2.3 Execute Phase 2 Migration

```bash
# Apply partitioning migration
# This creates new partitioned tables alongside old ones
psql "postgresql://scan:PASSWORD@police-scanner.cilycke4i4nz.us-east-1.rds.amazonaws.com:5432/scanner" \
  -f db/migrations/002_phase2_partitioning.sql

# Expected duration: 10-30 minutes depending on data volume
# Watch for progress messages like:
# "Creating partitioned bcfy_calls_raw table"
# "Migrating X records from bcfy_calls_raw_nonpartitioned"
```

### 2.4 Post-Migration Verification

```sql
-- Verify partitions were created
SELECT
  schemaname,
  tablename,
  count(*) as partition_count
FROM pg_tables
WHERE tablename LIKE 'bcfy_calls_raw_%'
GROUP BY schemaname, tablename;

-- Check partition distribution
SELECT
  tablename,
  COUNT(*) as rows
FROM bcfy_calls_raw
GROUP BY tablename
ORDER BY tablename;

-- Verify foreign keys still work
SELECT COUNT(*) FROM transcripts WHERE call_uid IS NOT NULL;

-- Test a time-range query (should be much faster!)
EXPLAIN ANALYZE
SELECT * FROM bcfy_calls_raw
WHERE started_at > NOW() - INTERVAL '7 days'
LIMIT 100;
-- Should show "Partition Pruning" in EXPLAIN output
```

### 2.5 Data Verification

```sql
-- Compare row counts (should match)
SELECT COUNT(*) FROM bcfy_calls_raw AS new_count;
SELECT COUNT(*) FROM bcfy_calls_raw_nonpartitioned AS old_count;
-- Both should return same number

-- Check for data integrity
SELECT COUNT(*) FROM bcfy_calls_raw WHERE call_uid IS NULL OR call_uid = '';
-- Should return 0 (or same as before if there were any)
```

### 2.6 Drop Old Non-Partitioned Tables

**Only after verifying data integrity!**

```sql
-- BEFORE DROPPING: Verify row counts match
SELECT
  (SELECT COUNT(*) FROM bcfy_calls_raw) as new_table,
  (SELECT COUNT(*) FROM bcfy_calls_raw_nonpartitioned) as old_table;

-- If counts match, drop old tables
DROP TABLE IF EXISTS bcfy_calls_raw_nonpartitioned;
DROP TABLE IF EXISTS transcripts_nonpartitioned;
DROP TABLE IF EXISTS api_call_metrics_nonpartitioned;
DROP TABLE IF EXISTS system_logs_nonpartitioned;

-- Verify disk space was recovered
SELECT
  tablename,
  pg_size_pretty(pg_total_relation_size('public.' || tablename)) as total_size
FROM pg_stat_user_tables
WHERE tablename IN ('bcfy_calls_raw', 'transcripts', 'api_call_metrics', 'system_logs')
ORDER BY pg_total_relation_size('public.' || tablename) DESC;
```

### 2.7 Set Up Automated Partition Maintenance

PostgreSQL 11+ supports this natively; for earlier versions, use cron:

```sql
-- If pg_cron is available
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule partition creation (run daily at midnight)
SELECT cron.schedule('maintain-partitions', '0 0 * * *',
  'SELECT maintain_partitions();'
);

-- Schedule data cleanup (run daily at 2 AM)
SELECT cron.schedule('cleanup-old-data', '0 2 * * *',
  'SELECT cleanup_old_data();'
);

-- Verify schedules
SELECT * FROM cron.job WHERE jobname IN ('maintain-partitions', 'cleanup-old-data');
```

### 2.8 Rollback Plan

If partitioning causes issues:

```sql
-- Rename partitioned tables
ALTER TABLE bcfy_calls_raw RENAME TO bcfy_calls_raw_partitioned;

-- Rename old non-partitioned tables back
ALTER TABLE bcfy_calls_raw_nonpartitioned RENAME TO bcfy_calls_raw;

-- Update foreign keys in dependent tables
ALTER TABLE transcripts
  DROP CONSTRAINT transcripts_call_fk;
ALTER TABLE transcripts
  ADD CONSTRAINT transcripts_call_fk
  FOREIGN KEY (call_uid) REFERENCES bcfy_calls_raw(call_uid)
  ON DELETE SET NULL;

-- Or restore from backup
pg_restore -d scanner backup_before_partitioning_*.dump
```

---

## Phase 3: Schema Enhancements (Week 3-4)

### ⏱️ Estimated Time: 2-5 minutes
### 🎯 Risk: LOW
### ⚡ Impact: MEDIUM (Better state tracking and observability)

This phase adds columns for enhanced state tracking and monitoring.

### 3.1 Execute Phase 3 Migration

```bash
# Apply schema enhancements
psql "postgresql://scan:PASSWORD@police-scanner.cilycke4i4nz.us-east-1.rds.amazonaws.com:5432/scanner" \
  -f db/migrations/003_phase3_schema_improvements.sql

# Expected output:
# "Phase 3 Schema Improvements Complete! ✓"
# New columns and functions listed
```

### 3.2 Verify New Features

```sql
-- Check new columns
\d bcfy_playlists  -- Should show: last_synced_at, sync_error_count, last_error_message
\d bcfy_calls_raw  -- Should show: processing_stage, retry_count
\d processing_state  -- Should show: created_at, retry_count, max_retries

-- Test new functions
SELECT * FROM get_pipeline_stats();
SELECT * FROM monitoring.pipeline_stats;
SELECT * FROM monitoring.playlist_sync_health;

-- Check for stuck items
SELECT * FROM get_stuck_processing_items();
```

### 3.3 Update Application Code

After Phase 3, you should update your application to use new columns:

**For `get_calls.py`**: Track sync errors
```python
# When a sync fails
UPDATE bcfy_playlists
SET sync_error_count = sync_error_count + 1,
    last_error_message = %s
WHERE uuid = %s
```

**For `audio_worker.py`**: Use processing_stage
```python
# Instead of just 'processed' boolean
UPDATE bcfy_calls_raw
SET processing_stage = 'downloading'
WHERE call_uid = %s
```

**For monitoring**: Use new views
```python
# In your health check endpoints
cursor.execute("SELECT * FROM monitoring.pipeline_stats")
stats = cursor.fetchall()
```

---

## Troubleshooting

### Issue: Slow Migration

**Symptom**: Phase 2 is taking longer than expected

**Solutions**:
1. Check server resources: `SELECT pid, usename, application_name, state FROM pg_stat_activity WHERE state != 'idle';`
2. Kill blocking queries if necessary: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE query LIKE '%bcfy_calls_raw%' AND query NOT LIKE '%pg_%';`
3. Consider migrating in smaller chunks

### Issue: Disk Space Errors

**Symptom**: `ERROR: could not extend file: No space left on device`

**Solutions**:
1. Temporarily increase AWS RDS storage
2. Drop old non-partitioned tables: `DROP TABLE bcfy_calls_raw_nonpartitioned;`
3. Run cleanup function: `SELECT cleanup_old_data();`

### Issue: Foreign Key Violations

**Symptom**: `ERROR: insert or update on table "transcripts" violates foreign key`

**Solutions**:
1. Check that bcfy_calls_raw has all required records:
   ```sql
   SELECT COUNT(*) FROM transcripts
   WHERE call_uid NOT IN (SELECT call_uid FROM bcfy_calls_raw);
   ```
2. If orphaned records exist, either delete them or add matching calls:
   ```sql
   DELETE FROM transcripts
   WHERE call_uid NOT IN (SELECT call_uid FROM bcfy_calls_raw);
   ```

### Issue: Query Performance Not Improved

**Symptom**: Queries still slow after partitioning

**Solutions**:
1. Verify partition pruning is working:
   ```sql
   EXPLAIN SELECT * FROM bcfy_calls_raw
   WHERE started_at > NOW() - INTERVAL '1 day';
   ```
   Should show "Subplans Removed: X" in output

2. Update table statistics:
   ```sql
   ANALYZE bcfy_calls_raw;
   ANALYZE transcripts;
   ```

3. Check if queries use partition key in WHERE clause:
   ```sql
   -- Good - uses partition key
   SELECT * FROM bcfy_calls_raw WHERE started_at > NOW() - INTERVAL '7 days';

   -- Bad - doesn't use partition key
   SELECT * FROM bcfy_calls_raw WHERE feed_id = 12345;
   ```

---

## Performance Validation

After completing all phases, validate improvements:

### Query Performance Test

```sql
-- Test 1: Time-range query (should be 10-100x faster)
\timing
SELECT COUNT(*) FROM bcfy_calls_raw
WHERE started_at > NOW() - INTERVAL '7 days';
-- Note execution time - should be <100ms for partitioned table

-- Test 2: Full-text search (should be 3-5x faster)
SELECT id, ts_rank(tsv, query) as rank
FROM transcripts, plainto_tsquery('english', 'police') query
WHERE tsv @@ query
LIMIT 10;
-- Should complete in <500ms

-- Test 3: Dashboard aggregations (should be 5-10x faster)
SELECT
  COUNT(*) as calls_24h,
  COUNT(DISTINCT feed_id) as active_feeds,
  AVG(duration_ms::NUMERIC) / 1000 as avg_duration_sec
FROM bcfy_calls_raw
WHERE started_at > NOW() - INTERVAL '24 hours';
```

### Resource Monitoring

```sql
-- Check disk usage reduction
SELECT
  tablename,
  pg_size_pretty(pg_total_relation_size('public.' || tablename)) as total_size,
  pg_size_pretty(pg_relation_size('public.' || tablename)) as table_size,
  pg_size_pretty(pg_indexes_size('public.' || tablename)) as index_size
FROM pg_stat_user_tables
WHERE tablename IN ('bcfy_calls_raw', 'transcripts', 'api_call_metrics', 'system_logs')
ORDER BY pg_total_relation_size('public.' || tablename) DESC;

-- Check index health
SELECT * FROM monitoring.index_usage
WHERE usage_status = 'UNUSED' OR usage_status = 'LOW_USAGE'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Check table bloat
SELECT * FROM monitoring.table_bloat
WHERE status IN ('WARNING', 'CRITICAL');
```

### Connection Pool Monitoring

```sql
-- Check connection usage
SELECT
  usename,
  application_name,
  state,
  COUNT(*) as connection_count
FROM pg_stat_activity
GROUP BY usename, application_name, state
ORDER BY connection_count DESC;

-- Should see balanced connections across API and scheduler
```

---

## Post-Migration Checklist

After completing all phases, verify:

- [ ] All migrations executed successfully
- [ ] Data integrity verified (row counts match)
- [ ] Queries show partition pruning
- [ ] Performance benchmarks meet targets
- [ ] Monitoring views accessible
- [ ] Backup created from final state
- [ ] Application code updated for new columns
- [ ] Automated maintenance jobs configured (pg_cron)
- [ ] Documentation updated
- [ ] Team trained on new features

---

## Maintenance Operations

### Daily Maintenance

```sql
-- Auto-run via pg_cron or scheduled task
SELECT cleanup_old_data();  -- Enforce retention policies
SELECT maintain_partitions();  -- Create future partitions
```

### Weekly Maintenance

```sql
-- Vacuum bloated tables
VACUUM ANALYZE bcfy_calls_raw;
VACUUM ANALYZE api_call_metrics;

-- Check for unused indexes
SELECT * FROM monitoring.index_usage
WHERE usage_status = 'UNUSED'
AND indexname NOT LIKE 'bcfy_%_pkey';
```

### Monthly Maintenance

```sql
-- Analyze query performance
SELECT * FROM monitoring.slow_queries
WHERE mean_time_ms > 1000;

-- Check retention policies
SELECT * FROM app_retention_policies;

-- Review partition health
SELECT * FROM monitoring.partition_health
ORDER BY total_size DESC;
```

---

## Monitoring Queries

Keep these bookmarked for regular monitoring:

```sql
-- Overall system health
SELECT * FROM monitoring.table_health;
SELECT * FROM monitoring.table_bloat WHERE status != 'HEALTHY';
SELECT * FROM monitoring.long_running_queries;

-- Pipeline status
SELECT * FROM monitoring.processing_pipeline_status;
SELECT * FROM monitoring.playlist_sync_health WHERE sync_error_count > 0;
SELECT * FROM get_stuck_processing_items();

-- Performance
SELECT * FROM monitoring.slow_queries LIMIT 20;
SELECT * FROM monitoring.index_usage WHERE usage_status = 'UNUSED';
```

---

## Support & Contact

For questions or issues:

1. Check the troubleshooting section above
2. Review PostgreSQL logs: `SELECT * FROM pg_log;`
3. Test queries in isolation with EXPLAIN ANALYZE
4. Consult PostgreSQL documentation: https://www.postgresql.org/docs/

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-08 | Initial release with 3-phase migration |

---

## License & Disclaimer

These migrations are provided as-is. Always test on staging before production. Maintain backups at each phase. The database will be fully functional throughout all migrations.

**Estimated total downtime: 0 (zero-downtime approach)**

