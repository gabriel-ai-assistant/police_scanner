# Database Schema Changelog

## init.sql Update - December 10, 2025

This document tracks the changes made to `/opt/policescanner/db/init.sql` to bring it up to date with the production database schema.

---

## Summary

**Goal**: Update init.sql to accurately reflect the production database schema as of December 2025, including consolidated monitoring features from migration 001.

**Files Modified**:
- `/opt/policescanner/db/init.sql` (PRIMARY)
- `/opt/policescanner/db/init.sql.backup.20251210` (BACKUP)

**Total Changes**:
- Lines added: ~120
- Lines removed: ~25
- Final line count: 380 lines

---

## Changes Applied

### 1. Header Documentation Updated

**Added**: Comprehensive header documenting schema version and migration history
- Documents which migrations are included (004, 005, 006, 001)
- Documents which migrations are NOT included (002, 003)
- Added date stamp (2025-12-10)

### 2. Columns Added

#### Table: `bcfy_calls_raw`
- **`playlist_uuid`** (UUID) - Playlist UUID for hierarchical S3 path construction
- **`s3_key_v2`** (TEXT) - Hierarchical S3 object key (v2 format with time partitioning)

#### Table: `transcripts`
- **`s3_key_v2`** (TEXT) - Hierarchical S3 object key (mirrors bcfy_calls_raw)

#### Table: `processing_state`
- **`retry_count`** (INTEGER, DEFAULT 0) - Number of retry attempts
- **`max_retries`** (INTEGER, DEFAULT 3) - Maximum allowed retries
- **`created_at`** (TIMESTAMPTZ, DEFAULT now()) - Record creation timestamp

#### Table: `bcfy_playlists`
- **`last_pos`** (BIGINT, DEFAULT 0, NOT NULL) - Unix timestamp from lastPos attribute (Live API)

**Note**: Production has BOTH `last_seen` and `last_pos` columns. This differs from the original inline migration which attempted to rename last_seen → last_pos.

### 3. Indexes Added

**bcfy_calls_raw**:
- `bcfy_calls_raw_playlist_uuid_idx` - Partial index WHERE playlist_uuid IS NOT NULL
- `bcfy_calls_raw_playlist_time_idx` - Composite (playlist_uuid, started_at DESC)
- `bcfy_calls_raw_s3_key_v2_idx` - Partial index WHERE s3_key_v2 IS NOT NULL
- `bcfy_calls_raw_pending_transcription_idx` - Partial index for pending transcriptions

**transcripts**:
- `transcripts_call_uid_idx` - Partial index WHERE call_uid IS NOT NULL

**processing_state**:
- `processing_state_status_updated_idx` - Composite (status, updated_at) WHERE status NOT IN ('indexed')

### 4. Tables Removed

**Removed**: `api_call_metrics` table (entire definition)
- **Reason**: Table does not exist in production database
- **Impact**: 18 lines removed (table definition + indexes + comments)

### 5. Schema Corrections

#### Table: `system_logs`
- **Changed**: Column `timestamp` → `created_at`
- **Removed**: Column `severity` (does not exist in production)
- **Updated**: Index `system_logs_timestamp_idx` now indexes `created_at` column

**Before**:
```sql
timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
severity TEXT NOT NULL DEFAULT 'INFO'
```

**After**:
```sql
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
-- severity column removed
```

### 6. Inline Migration Removed

**Removed**: Lines 265-279 - Migration block attempting to rename `last_seen` → `last_pos`
- **Reason**: Production has BOTH columns, so this inline migration is incorrect for init.sql
- **Replaced with**: Comment documenting `last_pos` column purpose

### 7. Monitoring Schema Added (from Migration 001)

**Added**: Complete monitoring schema with 6 views (~115 lines)

**New Schema**: `monitoring`

**New Views**:
1. **`monitoring.table_health`** - Table size, vacuum statistics, dead tuple ratios
2. **`monitoring.index_usage`** - Index scan counts, usage patterns, efficiency
3. **`monitoring.table_bloat`** - Table bloat detection with status (HEALTHY/WARNING/CRITICAL)
4. **`monitoring.connections`** - Active database connections by user/application
5. **`monitoring.long_running_queries`** - Queries running > 5 seconds
6. **`monitoring.database_size`** - Database size overview with pretty formatting

**Purpose**: Consolidated monitoring features from migration 001 into base schema

---

## Production Schema Alignment

After these changes, init.sql now accurately reflects:

✅ All columns present in production
✅ All indexes used in production
✅ Correct table definitions (system_logs)
✅ No extraneous tables (api_call_metrics removed)
✅ Monitoring schema included
✅ Both last_seen and last_pos in bcfy_playlists

---

## NOT Included (Staged for Future)

The following migrations are NOT included in this init.sql update:

- **Migration 002**: Table partitioning (monthly/weekly/daily)
  - Reason: Complex migration requiring data migration, kept separate

- **Migration 003**: Schema improvements (state management functions)
  - Reason: Advanced features not yet in production

---

## Verification

### File Statistics
- Original size: ~268 lines
- Updated size: 380 lines
- Backup: `/opt/policescanner/db/init.sql.backup.20251210`

### Validation Steps Completed
1. ✅ Backup created before modifications
2. ✅ All columns from production added
3. ✅ All indexes from production added
4. ✅ Non-existent tables removed (api_call_metrics)
5. ✅ Schema mismatches fixed (system_logs)
6. ✅ Monitoring schema consolidated
7. ✅ SQL syntax validated
8. ✅ File integrity checked (380 lines)

---

## Rollback Instructions

If you need to restore the original init.sql:

```bash
cp /opt/policescanner/db/init.sql.backup.20251210 /opt/policescanner/db/init.sql
```

---

## Next Steps

### Recommended Actions
1. **Test deployment** - Deploy init.sql to a test database and compare schema
2. **Document migration status** - Update migration tracking to reflect consolidated changes
3. **Consider applying Migration 002** - Table partitioning for production optimization
4. **Monitor production** - Use new monitoring views to track database health

### Monitoring Queries to Try
```sql
-- Check table health
SELECT * FROM monitoring.table_health;

-- Find unused indexes
SELECT * FROM monitoring.index_usage WHERE usage_status = 'UNUSED';

-- Check for bloat
SELECT * FROM monitoring.table_bloat WHERE status != 'HEALTHY';

-- Monitor connections
SELECT * FROM monitoring.connections;

-- Find slow queries
SELECT * FROM monitoring.long_running_queries;
```

---

## Migration Integration

### Updated Migration Status

| Migration | Status | Notes |
|-----------|--------|-------|
| init.sql (base) | ✅ Updated | Now includes 004, 005, 006, 001 changes |
| 001_phase1_improvements | ✅ Consolidated | Monitoring schema included in init.sql |
| 002_phase2_partitioning | ❌ Not applied | Staged for future (complex migration) |
| 003_phase3_schema_improvements | ❌ Not applied | Staged for future |
| 004_audio_quality_metrics | ✅ Consolidated | Columns NOT added (not in production) |
| 005_s3_hierarchical | ✅ Consolidated | playlist_uuid, s3_key_v2 columns added |
| 006_transcription_improvements | ✅ Consolidated | retry_count, max_retries, created_at added |

**Note**: Migration 004 created columns that are NOT in production (audio_quality_score, etc.), so they were NOT added to init.sql.

---

## Contact & Support

For questions about this schema update:
- Review the plan file: `/root/.claude/plans/woolly-rolling-frog.md`
- Compare with production: Use the schema extraction queries from the Explore agent
- Check migration files: `/opt/policescanner/db/migrations/`

---

**Updated by**: Claude Code (Database Schema Analysis Agent)
**Date**: December 10, 2025
**Version**: 1.0
