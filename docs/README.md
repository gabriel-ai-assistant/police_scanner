# Police Scanner Analytics Platform - Documentation

Welcome to the documentation hub for the Police Scanner Analytics Platform. This directory contains comprehensive guides, architecture documentation, and deployment instructions.

## Quick Links

### Getting Started
- **[Local Development Guide](guides/local-development.md)** - Set up your development environment
- **[Contributing Guide](../CONTRIBUTING.md)** - How to contribute to this project
- **[Main README](../README.md)** - Project overview and quick start

### Architecture & Design
- **[System Architecture](../CLAUDE.md)** - Detailed architecture overview
- **[Database Schema](architecture/database-schema.md)** - Database structure and design

### Deployment
- **[Deployment Checklist](deployment/deployment-checklist.md)** - Production deployment guide
- **[Audio Enhancement Deployment](deployment/audio-enhancement.md)** - Audio processing pipeline deployment
- **[Production Checklist](deployment/production-checklist.md)** - Pre-deployment verification

### Implementation Notes
- **[Implementation Summary](guides/implementation-summary.md)** - Development history and key decisions

## Documentation Structure

```
docs/
├── README.md                          # This file - documentation index
├── deployment/                        # Deployment guides
│   ├── deployment-checklist.md        # Main deployment guide
│   ├── audio-enhancement.md           # Audio processing deployment
│   └── production-checklist.md        # Pre-deployment verification
├── architecture/                      # Architecture documentation
│   └── database-schema.md             # Database schema reference
└── guides/                            # How-to guides
    ├── local-development.md           # Developer onboarding
    └── implementation-summary.md      # Implementation history
```

## Key Topics

### Development

**Setting Up Your Environment**
1. Read [Local Development Guide](guides/local-development.md)
2. Review [Contributing Guide](../CONTRIBUTING.md)
3. Check [CLAUDE.md](../CLAUDE.md) for architecture details

**Code Quality**
- Python: Configured with Ruff (see `pyproject.toml`)
- TypeScript: ESLint + Prettier (see `frontend/.eslintrc.json`)
- Tests: PyTest for backend, Jest for frontend

**Building & Running**
- Use `make` commands (see `Makefile`)
- Docker Compose for local services
- Scripts in `scripts/` directory

### Architecture

**System Components**
- **app_api**: FastAPI REST API server
- **app_scheduler**: APScheduler background job processor
- **app_transcribe**: Celery workers for Whisper transcription
- **frontend**: React 18 + TypeScript SPA

**Data Flow**
1. Broadcastify API → Scheduler (polling)
2. Scheduler → MinIO (audio storage)
3. MinIO → Transcription Workers (Whisper STT)
4. Transcription → PostgreSQL + MeiliSearch (indexing)
5. API → Frontend (serving data)

**External Services**
- PostgreSQL (AWS RDS) - Relational database
- Redis - Message broker & cache
- MeiliSearch - Full-text search
- MinIO - S3-compatible object storage

### Deployment

**Pre-Deployment Checklist**
- All tests pass (`make test`)
- Database migrations ready (`db/scripts/`)
- Environment variables configured (`.env`)
- Docker containers build successfully

**Deployment Process**
1. Review [Production Checklist](deployment/production-checklist.md)
2. Run deployment script: `make deploy` or `scripts/deploy.sh`
3. Verify health checks
4. Monitor logs

**Database Migrations**
- Migration files in `db/migrations/`
- Execution script: `db/scripts/execute-migrations.py`
- See [Database Schema](architecture/database-schema.md) for details

## Additional Resources

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- API Reference: See [CLAUDE.md](../CLAUDE.md) for endpoint list

### Troubleshooting
- Service-specific logs: `docker compose logs <service-name>`
- Debugging guide: [CLAUDE.md](../CLAUDE.md) - Troubleshooting sections
- Common issues: [Local Development Guide](guides/local-development.md)

### Community
- Issue Tracker: GitHub Issues
- Pull Requests: Use PR template (`.github/pull_request_template.md`)
- Discussions: GitHub Discussions

## Documentation Maintenance

This documentation is maintained alongside the codebase. When making changes:
1. Update relevant documentation files
2. Keep code examples current
3. Add new guides for new features
4. Archive outdated information

For questions or suggestions about documentation, please open an issue with the `documentation` label.
