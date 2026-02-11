# Police Scanner App — Production Readiness Bug Report

**Date:** 2026-02-11  
**Branch:** Fly-DB-Branch  
**Reviewer:** Automated Deep Review  

---

## 1. Critical Bugs

### BUG-001: Import of non-existent router modules crashes API on startup
- **File:** `app_api/main.py:14`
- **Severity:** Critical
- **Description:** The main module imports `notifications` and `webhooks` from `routers`, but these files do not exist (`app_api/routers/notifications.py` and `app_api/routers/webhooks.py` are missing). The API will crash immediately on startup with `ImportError`.
- **Fix:** Either create the missing router files or remove the imports and `include_router` calls.

### BUG-002: SQL injection via string interpolation in analytics router
- **File:** `app_api/routers/analytics.py:89`
- **Severity:** Critical
- **Description:** The `get_hourly_activity` endpoint uses Python `%` string formatting to inject the `hours` parameter directly into the SQL query: `INTERVAL '%s hours' % hours`. While `hours` is validated as an integer by FastAPI, this sets a dangerous precedent and bypasses asyncpg's parameterized query protection.
- **Fix:** Use parameterized queries: `WHERE started_at > NOW() - ($1 * INTERVAL '1 hour')` with the `hours` parameter passed as a bind variable.

### BUG-003: SQL injection via f-string in analytics top talkgroups
- **File:** `app_api/routers/analytics.py:111`
- **Severity:** Critical
- **Description:** The `period` query parameter is mapped to an interval string and inserted via f-string into the SQL query: `INTERVAL '{interval}'`. While the `period_map` lookup provides safety, if the default branch (`"24 hours"`) is reached, an unknown period value could still theoretically bypass. More critically, this pattern encourages copy-paste SQL injection elsewhere.
- **Fix:** Use parameterized interval or validated enum.

### BUG-004: SQL injection via string interpolation in monitor_data_integrity.py
- **File:** `app_scheduler/monitor_data_integrity.py:28,52,68,87`
- **Severity:** Critical
- **Description:** Multiple functions use `% hours` string interpolation directly in SQL queries (e.g., `INTERVAL '%s hours' % hours`). These are internal monitoring scripts but still a risk if parameters change.
- **Fix:** Use parameterized queries consistently.

### BUG-005: `get_call` returns error dict instead of raising HTTPException
- **File:** `app_api/routers/calls.py:47`
- **Severity:** High
- **Description:** When a call is not found, the endpoint returns `{"error": "Call not found"}` with a 200 status code instead of raising `HTTPException(status_code=404)`. This breaks API conventions and confuses clients.
- **Fix:** `raise HTTPException(status_code=404, detail="Call not found")`

### BUG-006: Hardcoded DB credentials in transcribe_audio.py
- **File:** `app_transcribe/transcribe_audio.py:9-14`
- **Severity:** Critical (Security)
- **Description:** Database credentials are hardcoded: `user: "scanner"`, `password: "scanner"`, `host: "db"`. These override environment variables and will fail in production.
- **Fix:** Use `os.getenv()` like the rest of the codebase.

---

## 2. Security Issues

### BUG-007: No authentication on geography mutation endpoints
- **File:** `app_api/routers/geography.py:43,80,115`
- **Severity:** High
- **Description:** The `PATCH /countries/{coid}`, `PATCH /states/{stid}`, and `PATCH /counties/{cntid}` endpoints have no auth protection. Any anonymous user can modify sync flags, potentially enabling/disabling data collection for entire regions.
- **Fix:** Add `require_admin` dependency to all PATCH geography endpoints.

### BUG-008: No authentication on calls, transcripts, analytics, playlists, system endpoints
- **File:** `app_api/routers/calls.py`, `transcripts.py`, `analytics.py`, `playlists.py`, `system.py`
- **Severity:** High
- **Description:** All these endpoints have no auth requirement. Sensitive data (calls, transcripts, system logs, API metrics) is publicly accessible. The `PATCH /playlists/{uuid}` endpoint allows unauthenticated users to modify playlist sync settings.
- **Fix:** Add `require_auth` or `require_admin` dependency to all endpoints.

### BUG-009: MinIO endpoint hardcoded with internal IP
- **File:** `app_api/config.py:24`
- **Severity:** Medium
- **Description:** `MINIO_ENDPOINT` defaults to `"192.168.1.152:9000"` which is a hardcoded internal IP address. This will fail in any other environment.
- **Fix:** Remove default or use a hostname-based default like `"minio:9000"`.

### BUG-010: SESSION_COOKIE_SECURE defaults to False
- **File:** `app_api/config.py:32`
- **Severity:** High
- **Description:** `SESSION_COOKIE_SECURE` defaults to `False`, meaning session cookies will be sent over HTTP in production if the env var is not set. The docker-compose sets it to `true`, but the code default is insecure.
- **Fix:** Default to `True` in code, override to `False` only for local dev.

### BUG-011: Flower monitoring has hardcoded default credentials
- **File:** `docker-compose.yml:152-153`
- **Severity:** Medium
- **Description:** Flower basic auth is hardcoded as `admin:changeme` in the compose file. If deployed without changing, the Celery task queue is exposed.
- **Fix:** Use environment variables for Flower credentials.

### BUG-012: `user_id` passed as string to UUID column queries
- **File:** `app_api/auth/dependencies.py:47`, `app_api/routers/auth.py:167`
- **Severity:** Medium
- **Description:** `CurrentUser.id` is stored as `str(row["id"])` but then used directly in queries like `WHERE id = $1` against a UUID column. While asyncpg may handle string-to-UUID coercion, this is fragile and may cause type mismatch errors.
- **Fix:** Store `id` as UUID or explicitly cast in queries.

### BUG-013: Admin user status endpoint takes `is_active` as query param, not body
- **File:** `app_api/routers/auth.py:222`
- **Severity:** Medium
- **Description:** `update_user_status` takes `is_active: bool` as a bare function parameter, which FastAPI interprets as a query parameter. Disabling a user via `PATCH /admin/users/{id}/status?is_active=false` is bad practice — should be a JSON body.
- **Fix:** Create a Pydantic model for the request body.

---

## 3. Data Integrity Issues

### BUG-014: audio_worker uses connection outside transaction for multi-step updates
- **File:** `app_scheduler/audio_worker.py:45-97`
- **Severity:** High
- **Description:** The audio worker acquires a single connection and uses `FOR UPDATE SKIP LOCKED` to claim rows, but then performs download/convert/upload operations on each row sequentially while holding the lock. If the worker crashes mid-batch, some rows may remain locked until the connection times out. Additionally, the individual UPDATE statements are not wrapped in explicit transactions.
- **Fix:** Use shorter-lived transactions per call, or at least wrap each call's processing in a transaction block.

### BUG-015: Race condition in db_pool connection management
- **File:** `app_scheduler/db_pool.py:10-19`
- **Severity:** Medium
- **Description:** `get_pool()` has a TOCTOU race: two concurrent coroutines could both see `_pool is None` and create duplicate pools. While unlikely in practice with asyncio's single-threaded model, it's still poor form.
- **Fix:** Use an asyncio Lock or ensure single-threaded initialization.

### BUG-016: `get_db()` in get_calls.py creates non-pooled connections
- **File:** `app_scheduler/get_calls.py:63`
- **Severity:** Low
- **Description:** `get_db()` creates a raw `asyncpg.connect()` connection, but the rest of the code uses the connection pool. This function appears unused but could cause connection leaks if called.
- **Fix:** Remove the unused function or redirect to pool.

### BUG-017: `insert_call` function (legacy) doesn't use playlist_uuid
- **File:** `app_scheduler/get_calls.py:217`
- **Severity:** Low
- **Description:** The legacy `insert_call` function doesn't set `playlist_uuid` or `feed_id`, so any calls inserted through it would have NULL playlist associations. This appears unused (replaced by `quick_insert_call_metadata`) but remains in the codebase.
- **Fix:** Remove the dead code.

---

## 4. API Issues

### BUG-018: Missing `Dashboard` page import in App.tsx
- **File:** `frontend/src/App.tsx:10`
- **Severity:** High
- **Description:** `Dashboard` is imported from `./pages/Dashboard` but there's no matching default export file at that exact path. Actually it exists based on the file listing — but `NotificationSettings` (line 15 of App.tsx imports) is imported but the file `pages/NotificationSettings.tsx` doesn't exist in the file listing.
- **Fix:** Create the missing `NotificationSettings.tsx` page or remove the import and route.

### BUG-019: `transcriptsToday` field typed as `str` instead of `int` in DashboardMetrics
- **File:** `app_api/models/analytics.py:27`
- **Severity:** Medium
- **Description:** `transcriptsToday: Optional[str] = None` should be `Optional[int]` to match the integer value being assigned.
- **Fix:** Change type to `Optional[int]`.

### BUG-020: Keyword analytics endpoint returns hardcoded mock data
- **File:** `app_api/routers/analytics.py:127-131`
- **Severity:** Medium
- **Description:** `get_keyword_hits` returns hardcoded placeholder data ("pursuit: 12, accident: 9, alarm: 7") instead of real data. This is misleading in production.
- **Fix:** Return empty list with a note, or implement the real query.

---

## 5. Frontend Issues

### BUG-021: API errors silently fall back to mock data in production
- **File:** `frontend/src/api/dashboard.ts` (multiple functions)
- **Severity:** High
- **Description:** All dashboard API functions catch errors and return mock data: `console.warn('Using mock ... due to API error', error); return mockData;`. In production, if the API is down, users see fake data instead of error states.
- **Fix:** Only fall back to mocks when `isMock()` is true. Throw errors in production mode.

### BUG-022: No error boundaries in the React app
- **File:** `frontend/src/App.tsx`
- **Severity:** Medium
- **Description:** There are no React error boundaries. Any uncaught JS error in a component tree will crash the entire app with a white screen.
- **Fix:** Add error boundaries at layout and page levels.

### BUG-023: Missing `NotificationSettings` page component
- **File:** `frontend/src/App.tsx:15`
- **Severity:** High
- **Description:** `NotificationSettings` is imported in App.tsx but the file doesn't exist in the pages directory. The app will crash at build time or on navigation to `/settings/notifications`.
- **Fix:** Create the component or remove the route.

### BUG-024: Dashboard page import references non-existent `types/dashboard.ts`
- **File:** `frontend/src/api/dashboard.ts:4`
- **Severity:** High
- **Description:** The dashboard API imports types from `@/types/dashboard` but this file doesn't exist in the types directory listing. Will cause build failures.
- **Fix:** Create the types file or move types inline.

---

## 6. Configuration Issues

### BUG-025: Docker Compose missing `app_api` dependency on postgres
- **File:** `docker-compose.yml:106`
- **Severity:** High
- **Description:** `app_api` depends on `redis` but NOT on `postgres`. The API will crash on startup if postgres isn't ready, since the lifespan creates a connection pool immediately.
- **Fix:** Add `postgres: condition: service_healthy` to `app_api.depends_on`.

### BUG-026: Docker Compose missing `app_scheduler` dependency on postgres
- **File:** `docker-compose.yml:90`
- **Severity:** High
- **Description:** `app_scheduler` has no dependency on `postgres` despite needing it immediately for ingestion. It depends only on `redis` and `signal-api`.
- **Fix:** Add postgres dependency.

### BUG-027: `app_transcription` missing dependency on postgres
- **File:** `docker-compose.yml:105`
- **Severity:** High
- **Description:** The transcription worker needs postgres for storing transcripts but only depends on `redis`.
- **Fix:** Add postgres dependency.

### BUG-028: Dual database config systems (env vars vs LOCAL_DB_*)
- **File:** `docker-compose.yml:33-37`
- **Severity:** Medium
- **Description:** Postgres container uses `LOCAL_DB_USER`, `LOCAL_DB_PASSWORD`, `LOCAL_DB_NAME` env vars for its own initialization, while applications use `PGUSER`, `PGPASSWORD`, `PGDATABASE`. If these don't match, the apps can't connect.
- **Fix:** Use the same env var names or document the relationship clearly.

### BUG-029: Missing volume for signal-cli data
- **File:** `docker-compose.yml:80`
- **Severity:** Low
- **Description:** `signal-api` mounts `./data/signal-cli` as a bind mount, while a `signal-cli-data` named volume is declared but never used. Bind mount may not exist on first run.
- **Fix:** Use the named volume or ensure the directory exists.

---

## 7. Performance Issues

### BUG-030: N+1 query pattern in county fetching
- **File:** `app_scheduler/get_counties.py:118-136`
- **Severity:** Medium
- **Description:** For each county in a state's county list, an individual HTTP request is made to fetch details, with a `time.sleep(0.1)` between each. For states with 100+ counties, this takes 10+ seconds per state.
- **Fix:** Check if a batch API endpoint exists, or parallelize with asyncio.

### BUG-031: Dashboard stats run 3 separate sequential queries without caching
- **File:** `app_api/routers/dashboard.py:186-217`
- **Severity:** Medium
- **Description:** `get_dashboard_stats` runs 3 separate COUNT queries with JOINs against potentially large tables, with no caching. Called on every dashboard load with the refresh interval.
- **Fix:** Combine into a single query or add Redis caching with the configured `CACHE_DASHBOARD_TTL`.

### BUG-032: Redis configured but never used for caching
- **File:** `app_api/config.py:17`, all routers
- **Severity:** Medium
- **Description:** `REDIS_URL` and cache TTL settings (`CACHE_DASHBOARD_TTL`, `CACHE_GEOGRAPHY_TTL`, `CACHE_PLAYLISTS_TTL`) are configured but no caching is actually implemented in any router.
- **Fix:** Implement Redis caching for expensive queries.

### BUG-033: S3 presigned URLs generated per-row in dashboard queries
- **File:** `app_api/routers/dashboard.py:60-71`
- **Severity:** Medium
- **Description:** `build_audio_url()` makes a boto3 `generate_presigned_url` call for every row in recent-calls and recent-activity queries. With 10-50 rows, this adds latency.
- **Fix:** Generate URLs in bulk or lazily on the frontend.

### BUG-034: Global S3 client in dashboard.py is not thread-safe for async
- **File:** `app_api/routers/dashboard.py:42-52`
- **Severity:** Medium
- **Description:** `get_s3_client()` creates a global boto3 client. Boto3 clients are not guaranteed to be safe for concurrent use in async contexts.
- **Fix:** Use a per-request client or add locking.

---

## 8. Production Readiness Issues

### BUG-035: No graceful shutdown for scheduler
- **File:** `app_scheduler/scheduler.py:69-74`
- **Severity:** Medium
- **Description:** The scheduler catches `KeyboardInterrupt`/`SystemExit` but doesn't close the database pool (`close_pool()` from db_pool is never called), potentially leaving dangling connections.
- **Fix:** Add pool cleanup in the shutdown path.

### BUG-036: No health check endpoint for scheduler service
- **File:** `app_scheduler/scheduler.py`
- **Severity:** Medium
- **Description:** The scheduler has no health check endpoint. Docker can't verify if it's actually processing jobs. The compose file has no healthcheck for this service.
- **Fix:** Add a simple HTTP health endpoint or file-based health check.

### BUG-037: No health check for transcription worker
- **File:** `app_transcribe/worker.py`
- **Severity:** Medium
- **Description:** The Celery worker has a `health_check` task but no HTTP endpoint. Docker can't health-check it.
- **Fix:** Add Celery inspect-based health check to compose.

### BUG-038: MeiliSearch initialization not resilient
- **File:** `app_transcribe/worker.py:63-65`
- **Severity:** High
- **Description:** MeiliSearch client is initialized at module level. If MeiliSearch is down when the worker starts, it won't retry — it will just fail all indexing calls silently. The `MEILI_MASTER_KEY` env var may also be missing.
- **Fix:** Initialize lazily with retry logic, and handle missing key gracefully.

### BUG-039: OpenAI client initialized at module level without key validation
- **File:** `app_transcribe/worker.py:56-58`
- **Severity:** Medium
- **Description:** `openai_client` is set to `None` if `OPENAI_API_KEY` is missing, but the warning is only logged. Tasks will fail at runtime with an unclear error.
- **Fix:** Fail fast at worker startup if the API key is missing.

### BUG-040: Temp files may leak on worker crash
- **File:** `app_scheduler/get_calls.py:310-317`, `app_transcribe/worker.py:202-205`
- **Severity:** Low
- **Description:** Audio temp files in `/app/shared_bcfy/tmp` are cleaned up on success but may accumulate on crashes. No periodic cleanup exists.
- **Fix:** Add a periodic temp directory cleanup task.

### BUG-041: Logging to system_logs table on every ingestion cycle
- **File:** `app_scheduler/get_calls.py:316,357-368`
- **Severity:** Low
- **Description:** Every 10-second ingestion cycle inserts 2+ rows into `system_logs` (cycle_start + cycle_complete + per-playlist). At 8,640 cycles/day, this is ~25,000+ log rows/day minimum. No log rotation/cleanup exists.
- **Fix:** Add log rotation or reduce logging frequency. Log only non-trivial cycles.

### BUG-042: No database migration runner in Docker startup
- **File:** `docker-compose.yml`
- **Severity:** High
- **Description:** There's no migration step in the Docker Compose workflow. The `db/` directory has migrations but no automated way to run them on deployment.
- **Fix:** Add an init container or startup script to run migrations.

### BUG-043: Geocoder service model mismatch with API router
- **File:** `services/geocoder/app/models.py` vs `app_api/models/locations.py`
- **Severity:** Low
- **Description:** The geocoder service has its own `Location`, `LocationWithContext`, `HeatmapPoint`, etc. models that differ slightly from the API's models (e.g., geocoder's `HeatmapPoint.most_recent` is required `datetime`, API's is `Optional[datetime]`). This could cause serialization mismatches.
- **Fix:** Share models or ensure compatibility.

### BUG-044: `transcribe_audio.py` uses `faster_whisper` with CUDA, conflicts with `worker.py` using OpenAI API
- **File:** `app_transcribe/transcribe_audio.py` vs `app_transcribe/worker.py`
- **Severity:** Medium
- **Description:** Two transcription implementations exist: `transcribe_audio.py` (local faster-whisper with CUDA) and `worker.py` (OpenAI Whisper API via Celery). Only `worker.py` is used in Docker Compose. `transcribe_audio.py` has hardcoded credentials and references a non-existent `s3_path` column. Dead code that could be confusingly invoked.
- **Fix:** Remove `transcribe_audio.py` or clearly mark it as deprecated.

### BUG-045: `parse_and_alert.py` references config.yaml that may not exist
- **File:** `app_transcribe/parse_and_alert.py:9`
- **Severity:** Medium
- **Description:** Script calls `sys.exit(1)` if `config.yaml` is missing. It also uses `signal-cli` for alerting which is a separate system from the Signal API in Docker. This script appears to be legacy/standalone and not integrated with the main pipeline.
- **Fix:** Remove or integrate into the main alerting system.
