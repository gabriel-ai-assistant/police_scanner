# Police Scanner Analytics Platform

## Overview

This is a **real-time police scanner audio processing and analytics platform** that ingests live audio feeds from Broadcastify, transcribes them using OpenAI's Whisper model, indexes transcripts for search, and provides analytics dashboards. The system processes thousands of emergency dispatch calls continuously, extracting metadata, audio, and full-text transcriptions.

**Technology Stack**: Python (FastAPI, Celery, APScheduler), TypeScript (React 18), PostgreSQL, Redis, MeiliSearch, MinIO S3 storage, Whisper STT

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                       BROADCASTIFY API                               │
│                    (Police Scanner Feeds)                            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                    ┌───────────┴────────────┐
                    │                        │
        ┌───────────▼──────────┐  ┌──────────▼──────────┐
        │  app_scheduler       │  │  Frontend/API       │
        │  (APScheduler)       │  │  (React + FastAPI)  │
        │                      │  │                     │
        │ • Fetch new calls    │  │ • Serve dashboards  │
        │ • Download audio MP3 │  │ • Query transcripts │
        │ • Extract features   │  │ • Search API        │
        └────────┬─────────────┘  └─────────┬──────────┘
                 │                          │
        ┌────────▼──────────┐       ┌──────▼──────────┐
        │   MinIO (S3)      │       │  Redis Cache    │
        │   Audio Storage   │       │  Job Queue      │
        └────────┬──────────┘       └────────┬────────┘
                 │                          │
        ┌────────▼──────────┐       ┌──────▼──────────┐
        │ app_transcription │       │ PostgreSQL RDS  │
        │ (Celery Workers)  │       │ (All metadata)  │
        │                   │       │                 │
        │ • Whisper STT     │       │ • Calls         │
        │ • Index to search │       │ • Transcripts   │
        └────────┬──────────┘       │ • Playlists     │
                 │                  │ • Geography     │
                 └──────┬───────────┘ • Monitoring    │
                        │             └─────────────┘
                 ┌──────▼──────────┐
                 │ MeiliSearch     │
                 │ Full-Text Index │
                 └─────────────────┘
```

---

## Services

| Service | Container Name | Port | Purpose | Key Tech | Dependencies |
|---------|---|---|---|---|---|
| **app_api** | scanner-api | 8000 | REST API backend | FastAPI, asyncpg | postgres, redis |
| **app_scheduler** | app-scheduler | - | Background job scheduler | APScheduler, asyncio | redis, postgres |
| **app_transcription** | scanner-transcription | - | Audio transcription workers | Celery, Whisper | redis, postgres, minio |
| **frontend** | scanner-frontend | 80 | Web UI (React SPA) | React 18, Vite, Nginx | scanner-api |
| **redis** | - | 6379 | Message broker & cache | Redis 7 | - |
| **meilisearch** | - | 7700 | Full-text search engine | MeiliSearch v1.11 | - |
| **PostgreSQL** | *external* | 5432 | Persistent database (AWS RDS) | PostgreSQL | - |
| **MinIO** | *external* | 9000 | S3-compatible storage | MinIO | - |

---

## Data Flow

### 1. Audio Ingest (every 10 seconds)
```
Broadcastify API
  ↓
app_scheduler/get_calls.py
  ├─ HTTP GET to https://api.broadcastify.com/calls
  ├─ JWT authentication (HMAC-SHA256)
  └─ INSERT INTO bcfy_calls_raw (call_uid, started_at, url, etc.)
```

### 2. Audio Download & Processing (every 5 seconds)
```
app_scheduler/audio_worker.py
  ├─ SELECT FROM bcfy_calls_raw WHERE processed = FALSE
  ├─ Download MP3 from call URL
  ├─ Extract features with librosa
  ├─ Upload to MinIO: s3://feeds/{call_uid}.mp3
  ├─ Queue Celery task to Redis
  └─ UPDATE bcfy_calls_raw SET processed = TRUE
```

### 3. Transcription & Indexing
```
app_transcription/worker.py (Celery)
  ├─ Dequeue task from Redis
  ├─ Download MP3 from MinIO
  ├─ Whisper.transcribe(audio_file) → text
  ├─ INSERT INTO transcripts (call_uid, text, tsvector)
  ├─ MeiliSearch.documents.create(transcript)
  ├─ UPDATE processing_state to 'indexed'
  └─ Log to system_logs
```

### 4. API Serving
```
app_api/routers
  ├─ GET /api/calls → PostgreSQL bcfy_calls_raw
  ├─ GET /api/transcripts → PostgreSQL transcripts
  ├─ GET /api/transcripts/search → MeiliSearch query
  ├─ GET /api/analytics → Dashboard aggregations
  ├─ GET /api/playlists → Feed management
  └─ GET /api/geography → Countries/states/counties (cached 1hr)
```

### 5. Frontend Display
```
React App (localhost:80 or localhost:3000)
  ├─ Dashboard → GET /api/analytics
  ├─ Calls List → GET /api/calls?limit=50
  ├─ Search → POST /api/transcripts/search?q=keyword
  ├─ Feed Settings → GET/POST /api/playlists
  └─ Admin → GET /api/system
```

---

## Directory Structure

```
/opt/policescanner/
├── app_api/                          # FastAPI REST API service
│   ├── main.py                       # FastAPI app, lifespan, CORS
│   ├── config.py                     # Pydantic Settings (database_url, cors_origins)
│   ├── database.py                   # AsyncPG connection pool (5-20 conn)
│   ├── routers/                      # API endpoint modules
│   │   ├── calls.py                  # GET/POST /api/calls
│   │   ├── playlists.py              # Feed CRUD operations
│   │   ├── transcripts.py            # Transcript search & retrieval
│   │   ├── analytics.py              # Dashboard metrics aggregations
│   │   ├── geography.py              # Countries/states/counties (cached)
│   │   ├── system.py                 # System monitoring endpoints
│   │   └── health.py                 # Health checks
│   └── models/                       # Pydantic schemas (request/response)
│       ├── calls.py, playlists.py, transcripts.py, analytics.py
│       └── geography.py, system.py
│
├── app_scheduler/                    # APScheduler background jobs
│   ├── scheduler.py                  # Main scheduler (AsyncIOScheduler)
│   ├── get_calls.py                  # Broadcastify API ingest (JWT auth)
│   ├── get_cache_common_data.py      # Refresh geographic metadata (24h)
│   ├── audio_worker.py               # Download/process audio files
│   └── requirements.txt              # librosa, numpy, soundfile, etc.
│
├── app_transcribe/                   # Celery workers
│   ├── worker.py                     # Celery app, broker=Redis
│   ├── transcribe_audio.py           # Whisper transcription task
│   ├── parse_and_alert.py            # Post-processing & alerts
│   └── requirements.txt              # celery, openai-whisper, meilisearch
│
├── frontend/                         # React SPA
│   ├── src/
│   │   ├── main.tsx                  # React entrypoint
│   │   ├── App.tsx                   # Router (React Router v6)
│   │   ├── pages/                    # Route components
│   │   │   ├── Dashboard.tsx         # Main analytics view
│   │   │   ├── Feeds.tsx             # Playlist management
│   │   │   ├── Calls.tsx             # Call list
│   │   │   ├── Search.tsx            # Transcript search
│   │   │   ├── Settings.tsx
│   │   │   └── Admin.tsx
│   │   ├── components/               # Reusable UI components
│   │   │   ├── Navbar.tsx, Sidebar.tsx
│   │   │   ├── SearchBar.tsx
│   │   │   ├── TranscriptViewer.tsx
│   │   │   └── ui/                   # Radix UI primitives
│   │   ├── api/                      # Axios API client
│   │   │   ├── calls.ts, transcripts.ts, analytics.ts
│   │   │   └── geography.ts
│   │   ├── types/                    # TypeScript interfaces
│   │   │   ├── call.ts, feed.ts, transcript.ts
│   │   │   └── index.ts
│   │   └── hooks/                    # React custom hooks
│   ├── nginx.conf                    # Production web server config
│   └── package.json                  # Dependencies (React 18, Recharts, TanStack Query)
│
├── shared_bcfy/                      # Shared utilities
│   ├── auth.py                       # Broadcastify JWT generation
│   ├── token_cache.py                # JWT token cache (1hr expiry)
│   └── tmp/                          # Temporary file storage
│
├── db/                               # Database schemas & migrations
│   ├── init.sql                      # Original schema (10 tables)
│   ├── migrations/
│   │   ├── 001_phase1_improvements.sql  # Indexes & constraints
│   │   ├── 002_phase2_partitioning.sql  # Table partitioning by time
│   │   └── 003_phase3_schema_improvements.sql # State machine & views
│   ├── execute_migrations.py         # Python migration runner
│   ├── migration_validator.py        # Post-migration validation
│   ├── monitoring_queries.sql        # Performance monitoring
│   └── README_EXPERT_DBA_ANALYSIS.md # Optimization guide
│
├── conf/                             # Configuration templates
│   └── (deployment config examples)
│
├── .claude/                          # Claude Code configurations
│   └── (agent settings)
│
├── .env                              # Environment variables (35 vars)
├── .env.example                      # Template
├── .gitignore
├── docker-compose.yml                # Service orchestration
└── CLAUDE.md                         # This file
```

---

## Database Schema

### Core Tables

**Geographic Metadata**
- `bcfy_countries` - Master list of countries (coid PK)
- `bcfy_states` - US states (stid PK, coid FK)
- `bcfy_counties` - County/region data (cntid PK, stid FK, lat/lon)

**Feed Management**
- `bcfy_playlists` - Active scanner feeds (uuid PK, feed_name, listeners, groups_json)
- `bcfy_playlist_poll_log` - Poll history (uuid + poll_started_at composite PK)

**Call & Transcription Data**
- `bcfy_calls_raw` - Call metadata from Broadcastify (call_uid PK, started_at, url, processed flag)
- `transcripts` - Whisper transcriptions (id SERIAL, call_uid FK, text, tsvector for FTS)

**Processing Pipeline**
- `processing_state` - State machine tracking (call_uid PK, state: queued→downloaded→transcribed→indexed)

**Monitoring**
- `system_logs` - Event logs (timestamp, component, event_type, severity)
- `api_call_metrics` - API performance tracking (endpoint, duration_ms, cache_hit)

### Key Indexes
- GIN index on `transcripts.tsvector` for full-text search
- BTREE index on `bcfy_calls_raw.started_at` for time-range queries
- Composite index on `bcfy_calls_raw(processed, started_at)`

### Optimization Migrations (Ready to deploy)
Three-phase improvement plan in `/opt/policescanner/db/migrations/`:
1. **Phase 1**: Add 15+ performance indexes, constraints, monitoring views
2. **Phase 2**: Implement table partitioning by date (monthly for calls/transcripts)
3. **Phase 3**: Enhanced state machine, data retention automation

See `db/README_EXPERT_DBA_ANALYSIS.md` for detailed optimization strategy.

---

## Environment Variables

### Database Connection
```
PGHOST=<AWS RDS endpoint>
PGPORT=5432
PGUSER=<username>
PGPASSWORD=<password>
PGDATABASE=scanner
```

### Broadcastify API
```
BCFY_API_KEY=<API key>
BCFY_API_KEY_ID=<Key ID>
BCFY_APP_ID=<App ID>
BCFY_BASE_URL=https://api.broadcastify.com
BCFY_JWT_TOKEN=<JWT token (auto-generated)>
BCFY_COUNTRY_CODES=<comma-separated list>
BCFY_STATE_CODES=<comma-separated list>
```

### MinIO / S3 Storage
```
MINIO_ENDPOINT=192.168.1.152:9000
MINIO_ROOT_USER=<username>
MINIO_ROOT_PASSWORD=<password>
MINIO_BUCKET=feeds
```

### Search & Caching
```
MEILI_HOST=http://meilisearch:7700
MEILI_MASTER_KEY=<API key>
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
```

### AI & Processing
```
WHISPER_MODEL=small          # Options: tiny, base, small, medium, large
LANGUAGE=en                  # Transcription language code
CACHE_DASHBOARD_TTL=30       # Dashboard cache (seconds)
CACHE_GEOGRAPHY_TTL=3600     # Geography cache (seconds)
CACHE_PLAYLISTS_TTL=300      # Playlist cache (seconds)
```

---

## Quick Start Commands

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f scanner-api
docker compose logs -f scanner-transcription
docker compose logs -f app-scheduler

# Access running containers
docker compose exec scanner-api bash
docker compose exec scanner-transcription bash

# Stop all services
docker compose down

# Rebuild containers (after code changes)
docker compose build
docker compose up -d
```

---

## Troubleshooting & Agent Delegation

### Transcription Issues
**Symptoms**: Whisper tasks queued but not transcribing, no transcripts in database

**Debug Steps**:
1. Check Celery worker status: `docker compose logs scanner-transcription`
2. Check Redis queue: `redis-cli LLEN celery` (inside redis container)
3. Verify MinIO audio files exist: Check `192.168.1.152:9000`
4. Verify PostgreSQL connectivity from worker

**Delegate to**: `log-scanner` agent on `scanner-transcription` container

---

### API Issues
**Symptoms**: Endpoints returning 500 errors, slow responses, connection refused

**Debug Steps**:
1. Check API logs: `docker compose logs scanner-api`
2. Verify database connection: Check PostgreSQL RDS availability
3. Check Redis connectivity for caching
4. Verify CORS headers for frontend requests

**Delegate to**: `log-scanner` agent on `scanner-api` container

---

### Search Issues
**Symptoms**: Search returning no results or timeouts

**Debug Steps**:
1. Check MeiliSearch health: `curl http://localhost:7700/health`
2. Verify document indexing: Check index count in MeiliSearch UI
3. Check transcription indexing logs in system_logs table

**Delegate to**: `docker-ops` agent to check meilisearch health and restart if needed

---

### Scheduler Issues
**Symptoms**: New calls not being ingested, audio not being downloaded

**Debug Steps**:
1. Check scheduler logs: `docker compose logs app-scheduler`
2. Verify Broadcastify API credentials in .env
3. Check if scheduler process is running (should see APScheduler logs)
4. Check bcfy_calls_raw table for recent entries: `SELECT COUNT(*) FROM bcfy_calls_raw WHERE started_at > NOW() - INTERVAL '5 min'`

**Delegate to**: `log-scanner` agent on `app-scheduler` container

---

### Code Changes
**When modifying source code**, follow this sequence:

1. **Read and understand existing code**: Use `code-reader` agent
2. **Make targeted changes**: Use `fixer` agent
3. **Run tests**: Execute test suite
4. **Rebuild and restart**: `docker compose build && docker compose up -d`

---

## API Endpoints

### Calls
- `GET /api/calls` - List recent calls (paginated)
- `POST /api/calls` - Create call (admin)
- `GET /api/calls/{id}` - Get call details
- `DELETE /api/calls/{id}` - Delete call (admin)

### Transcripts
- `GET /api/transcripts` - List recent transcripts
- `POST /api/transcripts/search` - Full-text search (MeiliSearch)
- `GET /api/transcripts/{id}` - Get transcript details

### Playlists
- `GET /api/playlists` - List feeds
- `POST /api/playlists` - Create/update feed
- `DELETE /api/playlists/{id}` - Delete feed

### Analytics
- `GET /api/analytics/dashboard` - Dashboard metrics
- `GET /api/analytics/calls-by-hour` - Call frequency
- `GET /api/analytics/top-calls` - Most transcribed calls

### Geography
- `GET /api/geography/countries` - List all countries (cached 1hr)
- `GET /api/geography/states/{country_code}` - States by country
- `GET /api/geography/counties/{state_code}` - Counties by state

### System
- `GET /api/health` - Health check
- `GET /api/system/stats` - Processing pipeline stats
- `GET /api/system/logs` - System event logs

---

## Code Style & Standards

**Python (FastAPI, Celery, APScheduler)**
- Use type hints for all function signatures
- Use `async`/`await` for I/O-bound operations
- Log instead of print: `logger.info()`, `logger.error()`
- No hardcoded secrets (use environment variables)
- Asyncpg connection pooling for database access
- Pydantic models for request/response validation

**TypeScript (React, Vite)**
- Functional components with hooks
- React Router v6 for navigation
- TanStack Query for server state management
- Tailwind CSS for styling
- Axios for HTTP requests
- Type all props and return values

**Git & Commits**
- Use descriptive commit messages: "feat:", "fix:", "docs:", "refactor:"
- Keep commits atomic (one logical change per commit)
- Run tests before committing

---

## Forbidden Paths
Do not commit or expose:
- `.git/` - Git internals
- `__pycache__/` - Python cache
- `node_modules/` - Node dependencies
- `.env` - Environment secrets (use `.env.example` template)

---

## Key Configuration Files

- **docker-compose.yml** - Service orchestration
- **app_api/config.py** - Pydantic settings (database, CORS)
- **app_api/database.py** - AsyncPG pool configuration
- **.env** - Runtime environment variables
- **db/init.sql** - Database schema initialization
- **nginx.conf** - Frontend web server routing

---

## Related Documentation

- **Database Optimization**: `/opt/policescanner/db/README_EXPERT_DBA_ANALYSIS.md`
- **Migration Guide**: `/opt/policescanner/db/MIGRATION_GUIDE.md`
- **Database Quickstart**: `/opt/policescanner/db/START_HERE.md`

---

## Performance Characteristics

**API Response Times** (target):
- Calls list: <100ms (cached)
- Transcript search: <500ms (MeiliSearch)
- Analytics dashboard: <1s (cached)

**Data Throughput**:
- ~100-500 new calls/hour (depends on Broadcastify activity)
- ~5-10 transcription tasks in queue at any time
- ~1 transcription task completes every 30-60 seconds (depends on audio length)

**Storage**:
- PostgreSQL: ~500MB-2GB for 90 days of data
- MinIO: ~100MB-500MB for 90 days of audio files

---

## Next Steps & Improvements

1. **Deploy Phase 1 migration**: Add indexes and constraints (low-risk)
2. **Deploy Phase 2 migration**: Implement table partitioning (moderate complexity)
3. **Implement data retention**: Delete calls/transcripts older than 90 days
4. **Add monitoring alerts**: Integrate with PagerDuty or similar for job failures
5. **Scale transcription**: Increase Celery worker count for higher throughput
