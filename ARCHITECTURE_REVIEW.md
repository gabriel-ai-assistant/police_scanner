# Police Scanner App — Architectural Review

**Branch:** Fly-DB-Branch  
**Date:** 2026-02-11  
**Reviewer:** OpenClaw Architectural Review Agent

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Database Architecture](#2-database-architecture)
3. [API Design](#3-api-design)
4. [Authentication & Authorization](#4-authentication--authorization)
5. [Frontend Architecture](#5-frontend-architecture)
6. [Service Communication](#6-service-communication)
7. [Data Pipeline](#7-data-pipeline)
8. [Storage Strategy](#8-storage-strategy)
9. [DevOps & Infrastructure](#9-devops--infrastructure)
10. [Scalability Assessment](#10-scalability-assessment)
11. [Technical Debt](#11-technical-debt)
12. [Production Readiness Gaps](#12-production-readiness-gaps)
13. [Recommendations](#13-recommendations)

---

## 1. System Architecture Overview

### Services

The application is a **microservices-based police scanner data pipeline** composed of 10 Docker services:

| Service | Role | Port |
|---------|------|------|
| `frontend` | React SPA served via Nginx | 80 |
| `app_api` | FastAPI REST API | 8000 |
| `app_scheduler` | APScheduler-based ingestion, audio processing, transcription dispatch | — |
| `app_transcription` | Celery worker for OpenAI Whisper transcription | — |
| `geocoder` | FastAPI service for location extraction + Nominatim geocoding | 8001 |
| `postgres` | PostgreSQL 17 database | 5432 |
| `redis` | Message broker + cache | 6379 |
| `meilisearch` | Full-text search engine | 7700 |
| `signal-api` | Signal messaging for keyword alerts | 8080 |
| `flower` | Celery monitoring UI | 5555 |

### Data Flow Diagram

```
                        ┌─────────────────┐
                        │  Broadcastify    │
                        │  Live API        │
                        └────────┬────────┘
                                 │ JWT auth, polling every 10s
                                 ▼
                        ┌─────────────────┐
                        │  app_scheduler   │
                        │  (APScheduler)   │
                        │                  │
                        │  • get_calls     │──── Metadata INSERT ──→ PostgreSQL
                        │  • audio_worker  │──── MP3→WAV convert ──→ MinIO (S3)
                        │  • transcription │──── Celery task ──────→ Redis queue
                        │    dispatcher    │
                        └─────────────────┘
                                 │
                        ┌────────▼────────┐
                        │ app_transcription│
                        │  (Celery worker) │
                        │  OpenAI Whisper  │──── Transcript INSERT → PostgreSQL
                        │                  │──── Index ────────────→ MeiliSearch
                        └─────────────────┘
                                 │
                        ┌────────▼────────┐
                        │   geocoder       │
                        │  (FastAPI)       │──── Location INSERT ──→ PostgreSQL
                        │  Nominatim       │──── Cache queries ───→ geocode_cache
                        └─────────────────┘

   ┌──────────┐    /api/*     ┌──────────┐
   │ Frontend  │ ──────────→  │  app_api  │ ──→ PostgreSQL
   │ (React)   │  Nginx proxy │ (FastAPI) │ ──→ Redis (cache)
   │           │ ←────────── │           │ ──→ MinIO (presigned URLs)
   └──────────┘              └──────────┘
```

### Communication Patterns

- **Scheduler → PostgreSQL**: Direct asyncpg connection pool (async)
- **Scheduler → Redis**: Celery task dispatch (via `celery_app.send_task`)
- **Scheduler → MinIO**: boto3 S3 uploads
- **Transcription Worker → Redis**: Celery consumer
- **Transcription Worker → PostgreSQL**: psycopg2 (sync, per-task connections)
- **Transcription Worker → MeiliSearch**: HTTP client
- **API → PostgreSQL**: asyncpg connection pool
- **API → MinIO**: boto3 presigned URL generation
- **Frontend → API**: Axios HTTP via Nginx reverse proxy
- **Frontend → Firebase**: Client-side SDK for OAuth

**Strengths:**
- Clean separation of concerns across services
- Async-first architecture in scheduler and API
- Reasonable use of Redis as both broker and cache

**Weaknesses:**
- Geocoder service is isolated — no integration trigger from the transcription pipeline
- Signal-api service is declared as a dependency but alerting integration (`parse_and_alert.py`) uses file-based approach, not the REST API
- No service mesh or health-check-based orchestration beyond Docker restart policies

---

## 2. Database Architecture

### Schema Design

The schema is well-organized across **5 functional domains**:

1. **Geography cache** (`bcfy_countries`, `bcfy_states`, `bcfy_counties`) — Broadcastify hierarchy
2. **Ingestion** (`bcfy_playlists`, `bcfy_calls_raw`, `bcfy_playlist_poll_log`) — Raw call data
3. **Transcription** (`transcripts`, `processing_state`) — NLP pipeline
4. **User management** (`users`, `auth_audit_log`, `user_subscriptions`, `keyword_groups`, `keywords`, `subscription_keyword_groups`, `transcript_ratings`) — Auth + preferences
5. **Location intelligence** (`locations`, `geocode_cache`) — Geocoding
6. **Monitoring** (`system_logs`, `monitoring.*` views)

**Strengths:**
- `processing_state` provides a proper state machine (`queued` → `downloaded` → `transcribed` → `indexed` → `error`) with retry logic
- `bcfy_calls_raw` has a well-designed unique constraint on `(group_id, ts)` preventing duplicates
- Good use of partial indexes (e.g., `WHERE sync = TRUE`, `WHERE processed = TRUE`)
- `monitoring` schema with useful DBA views for table health, bloat, connections
- `tsvector` column on transcripts for full-text search (though MeiliSearch is primary)
- Hierarchical S3 key design (`playlist_id=UUID/YYYY/MM/DD/call_uid.wav`)

**Weaknesses:**
- **No partitioning applied** — Migrations 002 and 003 are staged but not executed. `bcfy_calls_raw` and `transcripts` will grow unbounded
- **`bcfy_calls_raw.call_uid` is TEXT** — derived as `{groupId}-{ts}`, could be more efficiently stored
- **`bcfy_counties` has duplicate PRIMARY KEY** — both `cntid INTEGER PRIMARY KEY` and `CONSTRAINT bcfy_counties_pkey PRIMARY KEY (cntid)` (harmless but messy)
- **`transcripts.tsv` index uses btree** instead of GIN — `CREATE INDEX ... USING btree(tsv)` is wrong for tsvector; should be `USING gin(tsv)`
- **No foreign key from `user_subscriptions` to `users`** visible in init.sql (defined in migration 008)
- **`api_call_metrics` table referenced in code** but not in init.sql schema — silently caught with `try/except UndefinedTableError`

### Migration Strategy

- 12 numbered SQL migration files in `db/migrations/`
- Manual execution via `db/run_migrations.py` and shell scripts
- No migration framework (no Alembic/Flyway) — migration state tracked manually
- `db/MIGRATION_GUIDE.md` and `db/START_HERE.md` provide documentation
- Risk levels annotated in migration headers (good practice)

### Connection Pooling

| Service | Library | Pool Config |
|---------|---------|-------------|
| `app_api` | asyncpg | min=5, max=20, timeout=60s |
| `app_scheduler` | asyncpg (db_pool.py) | min=2, max=10, timeout=60s |
| `app_transcription` | psycopg2 | **No pooling** — new connection per task |
| `geocoder` | asyncpg | min=2, max=10, timeout=60s |

**Critical issue:** The transcription worker creates a new psycopg2 connection for every Celery task and closes it in `finally`. Under load, this will exhaust PostgreSQL connections rapidly.

---

## 3. API Design

### Endpoint Organization

The API (`app_api/main.py`) is organized into 16 routers under `/api/`:

```
/api/health          — Health checks
/api/auth/*          — Session management, user profile
/api/admin/*         — User management (admin-only)
/api/calls/*         — Call metadata CRUD
/api/playlists/*     — Playlist management
/api/transcripts/*   — Transcript CRUD + search
/api/analytics/*     — Dashboard metrics
/api/geography/*     — Country/state/county hierarchy
/api/system/*        — System logs/status
/api/subscriptions/* — User feed subscriptions
/api/keyword-groups/* — Keyword group CRUD
/api/dashboard/*     — User-scoped dashboard
/api/ratings/*       — Transcript ratings
/api/notifications/* — Notification settings
/api/webhooks/*      — Signal webhook receiver
/api/locations/*     — Location data
```

**Strengths:**
- Clean router separation with one file per domain
- Pydantic models for request/response validation (`app_api/models/`)
- FastAPI dependency injection for DB pool and auth
- Health check endpoint with database connectivity test

**Weaknesses:**
- **No API versioning** — All endpoints are under `/api/` with no `v1/` prefix
- **No rate limiting** — No middleware for request throttling
- **No pagination metadata** — `list_calls` returns a list but no `total`, `next_page`, or cursor. Only `limit`/`offset` query params
- **Inconsistent response format** — Some endpoints return raw lists, others return `{"items": [...], "total": N}`. Dashboard endpoints return dual snake_case + camelCase fields (technical debt from frontend compatibility)
- **SQL injection surface** — `get_hourly_activity` in `analytics.py` uses f-string interpolation for the `hours` parameter: `INTERVAL '%s hours' % hours`. While the parameter is validated as `int` by FastAPI, this is a bad pattern. Same issue with `period_map` in `get_top_talkgroups`
- **Missing error handling** — `get_call` returns `{"error": "Call not found"}` instead of raising 404

### Response Transformation

Multiple `transform_*_response()` functions duplicate snake_case → camelCase conversion across routers (`auth.py`, `dashboard.py`, `calls.py`, `keyword_groups.py`). This is a cross-cutting concern that should be middleware or a shared utility.

---

## 4. Authentication & Authorization

### Flow

```
Client                    Firebase                  Backend
  │                          │                         │
  │─── signInWithGoogle() ──→│                         │
  │←── ID Token ────────────│                         │
  │                          │                         │
  │─── POST /auth/session {id_token} ────────────────→│
  │                          │  verify_id_token()      │
  │                          │←────────────────────────│
  │                          │                         │
  │←── Set-Cookie: scanner_session (httpOnly) ────────│
  │                          │                         │
  │─── GET /api/dashboard (cookie auto-included) ────→│
  │                          │  verify_session_cookie() │
  │←── Dashboard data ───────────────────────────────│
```

**Strengths:**
- **httpOnly session cookies** — tokens not accessible to JavaScript (XSS-safe)
- **Firebase Admin SDK** for server-side token verification (not trusting client claims)
- Clean dependency chain: `get_current_user_optional` → `require_auth` → `require_admin`
- Auth audit logging with IP address, user agent, event type
- Admin seeding via `ADMIN_EMAIL` env var (first matching login gets admin role)
- `shared_bcfy/` library provides JWT generation for Broadcastify API (separate from user auth)

**Weaknesses:**
- **`SESSION_COOKIE_SECURE` defaults to `False`** — must be True in production (HTTPS). Currently a footgun
- **No CSRF protection** — session cookies with `SameSite=lax` help, but POST endpoints have no CSRF token
- **No token refresh mechanism** — session cookie lasts 7 days. If Firebase revokes user, session stays valid until expiry (though `check_revoked=True` helps)
- **Most endpoints are unprotected** — `calls`, `playlists`, `transcripts`, `analytics`, `geography` routers have NO auth dependencies. Only `dashboard`, `subscriptions`, `keyword-groups`, `ratings` require auth
- **`get_current_user` is an alias for `get_current_user_optional`** — confusing; name implies it requires auth but returns `Optional[CurrentUser]`

### Shared Auth Library

`shared_bcfy/` contains `auth.py` (JWT generation for Broadcastify API) and `token_cache.py` (1-hour cache). This is **not** related to user authentication — it's for the external Broadcastify API. The naming is confusing since there's also `app_api/auth/`.

---

## 5. Frontend Architecture

### Tech Stack

- **React 18** + TypeScript + Vite
- **React Router v6** for routing
- **TanStack React Query v5** for server state
- **Axios** for HTTP
- **Tailwind CSS** + Radix UI primitives
- **Recharts** for data visualization
- **Firebase SDK** for client-side auth

### Component Hierarchy

```
App.tsx
├── Login (unprotected)
└── ProtectedRoute
    └── AppLayout
        ├── Sidebar
        ├── Navbar
        └── <Page>
            ├── Dashboard
            ├── Feeds → FeedList
            ├── Calls → CallTable
            ├── Search → SearchBar, TranscriptViewer
            ├── Map → LocationMap, MapControls, LocationPopup
            ├── Subscriptions / SubscriptionDetail
            ├── KeywordGroups / KeywordGroupDetail
            ├── Settings / NotificationSettings
            └── Admin → GeographyTree, ProcessingPipeline, PlaylistManager
```

### API Layer

Two-tier API abstraction:
1. `src/lib/api.ts` — Axios instance with `withCredentials: true`
2. `src/api/*.ts` — Domain-specific API modules (`calls.ts`, `feeds.ts`, `transcripts.ts`, etc.)
3. `src/api/client.ts` — Re-exports with localStorage override for API base URL

**Strengths:**
- Clean page-per-route structure
- Radix UI + Tailwind is a solid component foundation
- Mock data support via `VITE_MOCK=1` flag
- `ProtectedRoute` with admin role gating
- `useRefreshInterval` custom hook for auto-refresh

**Weaknesses:**
- **No code splitting** — All routes imported eagerly in `App.tsx` (no `React.lazy()`)
- **No error boundaries** — `ErrorState` component exists but no React error boundary wrapper
- **Duplicate API base URL logic** — Both `src/lib/api.ts` and `src/api/client.ts` define `getCurrentApiBaseUrl()` and `setApiBaseUrl()` with slightly different implementations
- **No test files** — No test files visible in the frontend source
- **No global state management** — Auth context is the only context; other state appears to be per-component with no shared store (may be fine given React Query usage)
- **`Suspense` wraps content** in `AppLayout` but no lazy-loaded components to suspend on

---

## 6. Service Communication

### Patterns

| From → To | Mechanism | Pattern |
|-----------|-----------|---------|
| Scheduler → PostgreSQL | asyncpg pool | Direct DB writes |
| Scheduler → Redis | Celery `send_task()` | Task queue |
| Scheduler → MinIO | boto3 `upload_file()` | Direct upload |
| Transcription → Redis | Celery consumer | Task processing |
| Transcription → PostgreSQL | psycopg2 per-task | Direct DB writes |
| Transcription → MeiliSearch | HTTP client | Index documents |
| API → PostgreSQL | asyncpg pool | Direct DB reads |
| API → MinIO | boto3 presigned URLs | Signed URL generation |
| Frontend → API | HTTP (Axios) | REST via Nginx proxy |
| Frontend → Firebase | Firebase SDK | OAuth + token |
| Geocoder → PostgreSQL | asyncpg pool | Direct DB reads/writes |
| Geocoder → Nominatim | httpx | Rate-limited HTTP |

### Async Processing

The scheduler runs 4 jobs via APScheduler:
1. **`job_run_ingest`** (every 10s) — Polls Broadcastify Live API, inserts call metadata
2. **`job_process_audio`** (every 5s) — Downloads MP3, converts to WAV, uploads to MinIO
3. **`job_dispatch_transcriptions`** (every 30s) — Finds processed calls, queues Celery tasks
4. **`job_refresh_common`** (every 24h) — Refreshes geography cache

**Strengths:**
- `max_instances=1` + `coalesce=True` prevents job overlap
- `FOR UPDATE SKIP LOCKED` in audio_worker prevents concurrent processing of same call
- Parallel playlist processing with `asyncio.gather(*tasks, return_exceptions=True)`
- Exponential backoff in audio_worker retries

**Weaknesses:**
- **No dead letter queue** — Failed Celery tasks retry 3 times then are lost
- **Geocoder is disconnected** — No automatic trigger after transcription completes; requires manual API calls or backfill
- **Tight coupling** — `transcription_dispatcher.py` imports Celery app directly; no abstraction layer
- **Signal alerting (`parse_and_alert.py`) appears to be a legacy standalone script** — not integrated into the pipeline

---

## 7. Data Pipeline

### End-to-End Flow

```
1. INGESTION (every 10s)
   Broadcastify Live API → fetch_live_calls() → quick_insert_call_metadata()
   Result: bcfy_calls_raw row with processed=FALSE

2. AUDIO PROCESSING (every 5s)
   bcfy_calls_raw WHERE processed=FALSE
   → Download MP3 from Broadcastify URL
   → analyze_audio_enhanced() (librosa quality scoring)
   → Tiered FFmpeg processing (TIER1-CLEAN / TIER2-MODERATE / TIER3-POOR)
   → validate_wav_output() (sample rate, duration, silence check)
   → Upload WAV to MinIO (hierarchical S3 key)
   → UPDATE processed=TRUE, s3_key_v2=...

3. TRANSCRIPTION DISPATCH (every 30s)
   bcfy_calls_raw WHERE processed=TRUE AND no transcript
   → INSERT processing_state status='queued'
   → Celery send_task('transcription.transcribe')

4. TRANSCRIPTION (Celery worker)
   → Download WAV from MinIO (with legacy path fallback)
   → OpenAI Whisper API (verbose_json response)
   → Calculate confidence from avg_logprob
   → INSERT into transcripts table
   → Index in MeiliSearch
   → UPDATE processing_state status='indexed'

5. GEOCODING (manual/backfill)
   → Extract locations from transcript text (regex patterns)
   → Geocode via Nominatim (rate-limited, cached)
   → INSERT into locations table

6. DISPLAY (on-demand)
   → API queries PostgreSQL for calls/transcripts
   → Presigned MinIO URLs for audio playback
   → MeiliSearch for full-text search
   → Frontend renders dashboard, call tables, map
```

**Strengths:**
- **Tiered audio processing** is sophisticated — quality-based FFmpeg filter chains are genuinely well-engineered
- **Position-based polling** (`lastPos`) for incremental ingestion avoids re-fetching
- **Idempotency** — `ON CONFLICT DO NOTHING` for calls, transcript existence check before processing
- **Output validation** — WAV files validated for sample rate, duration, silence, clipping

**Weaknesses:**
- **3-stage pipeline with 45-second total latency** (10s ingest + 5s audio + 30s dispatch) before transcription even starts. The 30s dispatch interval is unnecessarily slow
- **No streaming/event-driven trigger** — Each stage polls independently rather than triggering the next stage
- **Geocoder not in pipeline** — Step 5 requires manual invocation

---

## 8. Storage Strategy

### MinIO / S3

- **Bucket:** `feeds` (single bucket)
- **Key format (v2):** `calls/playlist_id={UUID}/{YYYY}/{MM}/{DD}/call_{call_uid}.wav`
- **Key format (legacy):** `calls/{call_uid}.wav`
- **Metadata:** Playlist ID, timestamp, talkgroup, duration, codec, source feed
- **Content-Type:** `audio/wav`
- **Dual-read fallback:** Transcription worker tries v2 path first, falls back to legacy

**Strengths:**
- Hierarchical partitioning enables efficient lifecycle policies and prefix-based listing
- S3 object metadata enables out-of-band querying
- Presigned URLs for frontend audio playback (1-hour expiry)

**Weaknesses:**
- **MinIO not in docker-compose** — External dependency; no local development story
- **No lifecycle policies defined** — Audio files accumulate forever
- **No CDN** — Presigned URLs point directly to MinIO instance
- **WAV format** — Uncompressed PCM at 16kHz is ~256KB/min. Opus or AAC would be 10x smaller

### Redis

Used as:
1. Celery broker (task queue)
2. Celery result backend
3. (Planned) API response cache (mentioned in `config.py` `CACHE_*_TTL` settings but not implemented)

**Weaknesses:**
- Cache TTL settings defined but no caching code exists in the API
- No Redis persistence configuration in docker-compose (data lost on restart)
- No Redis password configured

### MeiliSearch

- Single `transcripts` index
- Documents: `{id, call_uid, text, language, indexed_at}`
- Used for full-text search from the frontend

**Weaknesses:**
- Index creation done via manual script (`conf/meili_create_index.sh`)
- No searchable/filterable attribute configuration visible
- Master key passed via env var but no API key rotation

---

## 9. DevOps & Infrastructure

### Docker Setup

- `docker-compose.yml` with 10 services
- JSON file logging with 50MB rotation (3 files) — good practice
- Health checks on postgres, signal-api, app_api, geocoder, frontend
- `restart: unless-stopped` on all services
- Named volumes for postgres-data and redisinsight-data

**Strengths:**
- Multi-stage Dockerfile for frontend (build + nginx runtime)
- `.dockerignore` for app_api
- Proper `depends_on` with conditions

**Weaknesses:**
- **No resource limits** (memory, CPU) on any container
- **No network isolation** — All services on default network
- **Transcription Dockerfile copies only `worker.py`** — Missing `transcribe_audio.py` and `parse_and_alert.py` (though `worker.py` is the primary)
- **Scheduler Dockerfile uses Python 3.12**, API/transcription use 3.11 — inconsistent
- **No `.env` validation** — Missing env vars cause runtime failures

### CI/CD

**`ci.yml`:**
- Backend tests: Python 3.11, pytest with coverage, ruff linting
- Frontend tests: Node 20, ESLint, Prettier, type-check
- Docker build verification (no push)
- Triggered on push/PR to main/develop

**`docker-build.yml`:**
- Builds and pushes to GHCR on version tags
- Matrix strategy for all 4 services
- GitHub Release creation with auto-changelog

**Strengths:**
- Comprehensive CI with linting, type checking, coverage
- Build cache with GitHub Actions cache

**Weaknesses:**
- **No integration tests** — Only unit tests, no end-to-end
- **No staging environment** — Tags push directly to registry
- **`deploy.sh` exists** but deployment strategy is unclear
- **No database migration in CI** — Tests may fail if schema is out of date
- **Geocoder service not built in CI** — Missing from docker-build matrix

### Monitoring

- `flower` for Celery task monitoring
- `redisinsight` for Redis inspection
- `system_logs` table for application-level logging
- `monitoring.*` PostgreSQL views for DBA work
- No APM (Application Performance Monitoring)
- No centralized log aggregation
- No alerting beyond Signal keyword matches

---

## 10. Scalability Assessment

### Bottlenecks

1. **Single scheduler instance** — All ingestion, audio processing, and dispatch in one container. Not horizontally scalable
2. **OpenAI Whisper API** — External API rate limits cap transcription throughput
3. **PostgreSQL single node** — No read replicas. Dashboard queries compete with ingestion writes
4. **Nominatim rate limit** (1 req/sec) — Geocoding backfill of thousands of locations takes hours
5. **Audio conversion** — CPU-bound FFmpeg + librosa in scheduler container; no GPU acceleration

### Horizontal Scaling Readiness

| Component | Scalable? | Notes |
|-----------|-----------|-------|
| Frontend | ✅ | Stateless Nginx, can run N replicas |
| API | ✅ | Stateless, shared DB pool. Needs load balancer |
| Transcription Worker | ✅ | Celery workers scale independently |
| Scheduler | ❌ | **Single instance only** — APScheduler with in-memory state, `max_instances=1` |
| Audio Worker | ❌ | **Embedded in scheduler** — Can't scale independently |
| Geocoder | ⚠️ | Stateless but rate-limited by Nominatim |
| PostgreSQL | ❌ | Single node, no replication configured |
| Redis | ⚠️ | Single node, no clustering |

### Key Limitation

The scheduler combines 4 different jobs (ingestion, audio, transcription dispatch, common data refresh) into one process. Audio processing should be a separate scalable worker (like transcription already is via Celery).

---

## 11. Technical Debt

### Critical

1. **JWT generation duplicated 3 times:**
   - `shared_bcfy/auth.py` — Used by scheduler via `token_cache.py`
   - `app_scheduler/get_cache_common_data.py` — Own `build_jwt()` function
   - `app_scheduler/get_playlists.py` — Own `build_jwt()` function with own `get_conn()`

2. **Database connection creation duplicated:**
   - `app_scheduler/db.py` — psycopg2 `get_conn()`
   - `app_scheduler/db_pool.py` — asyncpg pool
   - `app_scheduler/get_playlists.py` — Own psycopg2 `get_conn()`
   - `app_scheduler/get_cache_common_data.py` — Uses `db.get_conn()`
   - `app_transcribe/worker.py` — Own psycopg2 connection per task
   - `app_transcribe/transcribe_audio.py` — Hardcoded DB credentials (!)

3. **`transcribe_audio.py` has hardcoded database credentials:**
   ```python
   DB = {
       "host": os.getenv("DB_HOST", "db"),
       "port": "5432",
       "dbname": "scanner",
       "user": "scanner",
       "password": "scanner",
   }
   ```
   This file also uses `faster-whisper` with CUDA, while `worker.py` uses OpenAI API — **two different transcription backends exist**.

4. **Dual camelCase/snake_case response format** — Every router has `transform_*_response()` functions that add camelCase aliases alongside snake_case fields, doubling response payload size.

### Moderate

5. **`parse_and_alert.py` is a standalone script** — Uses `signal-cli` binary directly (not the signal-api REST service in docker-compose). Config-driven via YAML file that may not exist in the container.

6. **Frontend API layer duplication** — `src/lib/api.ts` and `src/api/client.ts` both export the same Axios instance with overlapping `getCurrentApiBaseUrl()` / `setApiBaseUrl()` functions.

7. **`get_cache_common_data.py`** uses synchronous `requests` + `psycopg2` while the scheduler runs async — blocks the event loop during the 24h refresh job.

8. **No shared config/models package** — Types/schemas defined independently in API models, scheduler code, and frontend TypeScript types.

### Minor

9. **Missing migration 011** — Migrations jump from 010 to 012
10. **`transcripts.tsv` btree index** — Should be GIN index for tsvector search
11. **Flower default credentials** — `admin:changeme` hardcoded in docker-compose
12. **`api_call_metrics` table** referenced in code but not in schema

---

## 12. Production Readiness Gaps

### Security
- [ ] `SESSION_COOKIE_SECURE` must be `True` (HTTPS only)
- [ ] Most API endpoints have no authentication
- [ ] No CSRF protection on mutation endpoints
- [ ] No input sanitization beyond Pydantic validation
- [ ] Flower/RedisInsight exposed without strong auth
- [ ] Redis has no password
- [ ] Hardcoded credentials in `transcribe_audio.py`
- [ ] No secrets management (env vars in `.env` file)
- [ ] Firebase service account JSON mounted as file — no rotation strategy

### Reliability
- [ ] No database backups scheduled (scripts exist but not automated)
- [ ] No Redis persistence
- [ ] No health-check-based alerting
- [ ] No circuit breaker for external APIs (Broadcastify, OpenAI, Nominatim)
- [ ] No graceful shutdown handling in scheduler
- [ ] Transcription worker creates new DB connection per task

### Observability
- [ ] No structured logging (format strings, not JSON)
- [ ] No distributed tracing
- [ ] No metrics export (Prometheus/StatsD)
- [ ] No centralized log aggregation
- [ ] No uptime monitoring

### Operations
- [ ] No database migration automation (manual SQL execution)
- [ ] No rollback strategy for migrations
- [ ] No canary/blue-green deployment
- [ ] No resource limits on containers
- [ ] No network segmentation

---

## 13. Recommendations

### P0 — Critical (Do Before Production)

1. **Protect all API endpoints** — Add `require_auth` dependency to calls, playlists, transcripts, analytics, geography routers. Currently anyone can read all data.

2. **Fix `SESSION_COOKIE_SECURE=True`** for production and enforce HTTPS.

3. **Remove hardcoded credentials** from `transcribe_audio.py`. Decide on one transcription backend (OpenAI API via `worker.py` or local `faster-whisper` via `transcribe_audio.py`) and delete the other.

4. **Add connection pooling to transcription worker** — Use `psycopg2.pool.ThreadedConnectionPool` or switch to asyncpg.

5. **Add Redis password** and restrict Flower/RedisInsight access.

### P1 — High Priority (First Month)

6. **Separate audio worker from scheduler** — Make it a Celery task like transcription, enabling horizontal scaling.

7. **Consolidate JWT generation** — Delete duplicates in `get_cache_common_data.py` and `get_playlists.py`; use `shared_bcfy/token_cache.py` everywhere.

8. **Implement API response caching** — The `CACHE_*_TTL` settings exist but aren't used. Add Redis caching for dashboard, geography, and playlist endpoints.

9. **Fix the tsvector index** — Change from btree to GIN for proper full-text search performance.

10. **Add rate limiting** — Use FastAPI middleware (e.g., `slowapi`) to prevent abuse.

11. **Standardize response format** — Pick camelCase or snake_case and use a single middleware for transformation. Remove dual-format responses.

### P2 — Medium Priority (Quarter)

12. **Implement table partitioning** — Apply migrations 002/003 for `bcfy_calls_raw` (by month) and `transcripts` (by month). Critical as data grows.

13. **Connect geocoder to pipeline** — After transcription completes, automatically trigger location extraction + geocoding.

14. **Add lazy loading to frontend** — Use `React.lazy()` for route-level code splitting.

15. **Adopt Alembic** for database migrations with version tracking and rollback support.

16. **Add structured logging** (JSON format) and ship to a log aggregation service.

17. **Add container resource limits** and network segmentation in docker-compose.

### P3 — Nice to Have

18. **Replace WAV with Opus/AAC** for 10x storage savings (after verifying Whisper API accepts the format).

19. **Add WebSocket** for real-time dashboard updates instead of polling.

20. **Add read replica** for PostgreSQL to separate read (API) from write (scheduler) workloads.

21. **Event-driven pipeline** — Replace polling intervals with Redis pub/sub or PostgreSQL LISTEN/NOTIFY to trigger immediate processing after each stage.

22. **Add E2E tests** — Playwright or Cypress for critical user flows.

---

## Summary

This is a well-structured application with a clear domain model and thoughtful engineering in areas like tiered audio processing and hierarchical S3 storage. The main architectural concerns are:

1. **Security exposure** — Most API endpoints are completely unprotected
2. **Tight coupling in scheduler** — Audio processing can't scale independently
3. **Significant code duplication** — JWT generation (3x), DB connections (5x), response transformation (6x)
4. **Missing production basics** — No rate limiting, no caching, no structured logging, no container resource limits

The foundation is solid. Addressing the P0 items would make this deployable; P1 items would make it production-grade.
