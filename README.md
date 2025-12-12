# Police Scanner Analytics Platform

A real-time police scanner audio processing and analytics platform that ingests live audio feeds from Broadcastify, transcribes them using OpenAI's Whisper model, indexes transcripts for full-text search, and provides comprehensive analytics dashboards.

## Key Features

- **Real-Time Audio Ingestion**: Continuous polling of Broadcastify API for scanner feeds across multiple jurisdictions
- **Automatic Transcription**: AI-powered speech-to-text using OpenAI Whisper (configurable model sizes)
- **Full-Text Search**: Lightning-fast transcript search powered by MeiliSearch
- **Analytics Dashboard**: Interactive visualizations of call volume, geographic distribution, and trends
- **S3 Storage**: Hierarchical audio file storage with MinIO (S3-compatible)
- **Scalable Architecture**: Microservices design with Docker Compose orchestration

## Technology Stack

**Backend Services** (Python 3.11):
- FastAPI - REST API server
- Celery - Distributed task queue for transcription
- APScheduler - Background job scheduler for feed polling
- AsyncPG - High-performance PostgreSQL driver

**Frontend** (TypeScript/React):
- React 18 with TypeScript
- Vite build tooling
- TanStack Query for server state
- Tailwind CSS + Radix UI components
- Recharts for data visualization

**Data & Infrastructure**:
- PostgreSQL (AWS RDS) - Relational database
- Redis - Message broker & caching
- MeiliSearch - Full-text search engine
- MinIO - S3-compatible object storage
- Docker & Docker Compose - Containerization

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Access to PostgreSQL database (AWS RDS or local)
- Broadcastify API credentials ([Sign up here](https://www.broadcastify.com/api))
- MinIO instance (or AWS S3)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd policescanner
   ```

2. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials, API keys, etc.
   ```

3. **Start all services**:
   ```bash
   docker compose up -d
   ```

4. **Access the application**:
   - Frontend: http://localhost:80
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - MeiliSearch: http://localhost:7700

### First-Time Setup

For detailed development setup instructions, see [docs/guides/local-development.md](docs/guides/local-development.md).

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│           Broadcastify API (Scanner Feeds)            │
└──────────────────┬───────────────────────────────────┘
                   │
        ┌──────────▼─────────┐
        │  app_scheduler     │  ← Polls every 10s
        │  (APScheduler)     │
        └──────────┬─────────┘
                   │
        ┌──────────▼─────────┐
        │  MinIO S3 Storage  │  ← Audio files
        └──────────┬─────────┘
                   │
        ┌──────────▼─────────┐
        │ app_transcription  │  ← Celery workers
        │ (Whisper STT)      │
        └──────────┬─────────┘
                   │
        ┌──────────▼─────────┐       ┌──────────────┐
        │   PostgreSQL RDS   │←──────┤   app_api    │
        └──────────┬─────────┘       │  (FastAPI)   │
                   │                 └──────┬───────┘
        ┌──────────▼─────────┐              │
        │    MeiliSearch     │              │
        │  (Full-Text Index) │              │
        └────────────────────┘              │
                                   ┌────────▼────────┐
                                   │    Frontend     │
                                   │  (React + Vite) │
                                   └─────────────────┘
```

For detailed architecture documentation, see [CLAUDE.md](CLAUDE.md).

## Project Structure

```
policescanner/
├── app_api/              # FastAPI REST API service
├── app_scheduler/        # APScheduler background jobs
├── app_transcribe/       # Celery transcription workers
├── frontend/             # React single-page application
├── shared_bcfy/          # Shared utilities (JWT auth, caching)
├── db/                   # Database schemas & migrations
├── docs/                 # Documentation
│   ├── deployment/       # Deployment guides
│   ├── architecture/     # Architecture docs
│   └── guides/           # How-to guides
├── scripts/              # Build & deployment automation
├── .github/              # CI/CD workflows & templates
└── docker-compose.yml    # Service orchestration
```

## Development

### Running Tests
```bash
make test                    # Run all test suites
pytest app_api/tests/        # API tests only
pytest app_scheduler/tests/  # Scheduler tests only
```

### Code Quality
```bash
make lint      # Run linters (ruff, eslint)
make format    # Auto-format code
```

### Build & Deploy
```bash
make build     # Build Docker containers
make up        # Start services
make down      # Stop services
make logs      # View service logs
```

## API Documentation

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Key endpoints:
- `GET /api/calls` - List recent calls
- `POST /api/transcripts/search` - Full-text search
- `GET /api/analytics/dashboard` - Dashboard metrics
- `GET /api/playlists` - Active scanner feeds

## Documentation

- **[Architecture Overview](CLAUDE.md)** - Detailed system architecture
- **[Contributing Guide](CONTRIBUTING.md)** - Development guidelines
- **[Deployment Checklist](docs/deployment/deployment-checklist.md)** - Production deployment
- **[Local Development](docs/guides/local-development.md)** - Developer onboarding
- **[Database Documentation](db/README.md)** - Schema & migrations

## Environment Variables

Required environment variables (see `.env.example`):
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - PostgreSQL connection
- `BCFY_API_KEY`, `BCFY_API_KEY_ID`, `BCFY_APP_ID` - Broadcastify API credentials
- `MINIO_ENDPOINT`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` - MinIO/S3 config
- `MEILI_HOST`, `MEILI_MASTER_KEY` - MeiliSearch connection
- `WHISPER_MODEL` - Transcription model size (tiny/base/small/medium/large)

## Deployment

For production deployment instructions, see:
- [Deployment Checklist](docs/deployment/deployment-checklist.md)
- [Audio Enhancement Deployment](docs/deployment/audio-enhancement.md)

## Performance Characteristics

- **API Response Times**: <100ms for cached calls, <500ms for search queries
- **Throughput**: ~100-500 new calls/hour (varies by feed activity)
- **Transcription**: ~1 task completes every 30-60 seconds
- **Storage**: ~500MB-2GB database for 90 days of data

## Troubleshooting

Common issues and solutions:

**Transcription not working**: Check Celery worker logs
```bash
docker compose logs scanner-transcription
```

**API errors**: Verify database connection and Redis availability
```bash
docker compose logs scanner-api
```

**Search not returning results**: Check MeiliSearch health
```bash
curl http://localhost:7700/health
```

For more detailed troubleshooting, see [CLAUDE.md](CLAUDE.md) - Sections on debugging each service.

## License

**Copyright (c) 2025. All rights reserved.**

This software is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited. See [LICENSE](LICENSE) for details.

## Support

For issues and questions:
- Review [CLAUDE.md](CLAUDE.md) for architecture details
- Check [docs/guides/local-development.md](docs/guides/local-development.md) for setup help
- Consult service-specific logs for debugging

---

**Built with** FastAPI, React, PostgreSQL, Redis, MeiliSearch, MinIO, Whisper, and Docker.
