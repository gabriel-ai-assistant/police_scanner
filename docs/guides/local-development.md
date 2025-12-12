# Local Development Guide

Complete guide for setting up and developing the Police Scanner Analytics Platform locally.

## Prerequisites

### Required Software
- **Docker** (20.10+) & **Docker Compose** (v2+)
- **Git** (2.30+)
- **Code Editor** (VS Code, PyCharm, or similar)

### Optional Tools
- **Python 3.11+** (for running services outside Docker)
- **Node.js 20+** (for frontend development outside Docker)
- **PostgreSQL client** (psql, for database inspection)
- **Make** (for using Makefile commands)

### External Services
- PostgreSQL database (AWS RDS or local instance)
- Broadcastify API account ([Sign up](https://www.broadcastify.com/api))
- MinIO instance or AWS S3 bucket

## Quick Start (5 Minutes)

### 1. Clone & Configure
```bash
git clone <repository-url>
cd policescanner
cp .env.example .env
# Edit .env with your credentials
```

### 2. Start Services
```bash
make up
# Or: docker compose up -d
```

### 3. Verify
```bash
# Check all services are running
make ps

# View logs
make logs

# Access services
open http://localhost:80        # Frontend
open http://localhost:8000/docs # API docs
```

## Detailed Setup

### Step 1: Environment Configuration

Edit `.env` with your actual credentials:

**Database (Required)**:
```bash
PGHOST=your-database-host.region.rds.amazonaws.com
PGUSER=your-db-username
PGPASSWORD=your-secure-password
PGDATABASE=scanner
```

**Broadcastify API (Required)**:
```bash
BCFY_API_KEY=your-api-key
BCFY_API_KEY_ID=your-key-id
BCFY_APP_ID=your-app-id
```

**MinIO/S3 (Required)**:
```bash
MINIO_ENDPOINT=your-minio-host:9000
MINIO_ROOT_USER=your-username
MINIO_ROOT_PASSWORD=your-password
```

**Optional Settings**:
```bash
WHISPER_MODEL=small  # Change to 'base' or 'tiny' for faster transcription
LOG_LEVEL=DEBUG      # Enable debug logging
```

### Step 2: Initialize Database

If using a fresh database:
```bash
# Run initial schema
psql -h $PGHOST -U $PGUSER -d $PGDATABASE -f db/init.sql

# Run migrations
python db/scripts/execute-migrations.py
```

### Step 3: Start Services

```bash
# Build and start all services
docker compose up -d

# Or use Makefile
make build
make up
```

## Development Workflow

### Making Code Changes

**Backend (Python)**:
1. Edit files in `app_api/`, `app_scheduler/`, or `app_transcribe/`
2. Rebuild affected service:
   ```bash
   docker compose build scanner-api
   docker compose up -d scanner-api
   ```
3. View logs: `docker compose logs -f scanner-api`

**Frontend (React)**:
1. Edit files in `frontend/src/`
2. Changes auto-reload with Vite hot module replacement
3. Or rebuild: `docker compose build scanner-frontend`

### Running Tests

**All tests**:
```bash
make test
```

**Backend only**:
```bash
pytest app_api/tests/ -v
pytest app_scheduler/tests/ -v
```

**Frontend only**:
```bash
cd frontend
npm test
```

**With coverage**:
```bash
make test-coverage
```

### Code Quality

**Linting**:
```bash
make lint               # All services
ruff check .            # Python only
cd frontend && npm run lint  # TypeScript only
```

**Formatting**:
```bash
make format             # Auto-format all code
ruff format .           # Python only
cd frontend && npm run format  # TypeScript only
```

## Common Tasks

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f scanner-api
docker compose logs -f app-scheduler
docker compose logs -f scanner-transcription
```

### Database Operations

**Connect to database**:
```bash
make db-shell
# Or: psql -h $PGHOST -U $PGUSER -d $PGDATABASE
```

**Run migrations**:
```bash
python db/scripts/execute-migrations.py
```

**Create backup**:
```bash
make db-backup
```

### Accessing Service Shells

```bash
make shell-api        # API container
make shell-scheduler  # Scheduler container
make shell-transcribe # Transcription container
```

### Clearing Data

**Clean build artifacts**:
```bash
make clean
```

**Full reset (including volumes)**:
```bash
make clean-all
docker volume prune
```

## Troubleshooting

### Service Won't Start

**Check logs**:
```bash
docker compose logs <service-name>
```

**Common issues**:
- Missing environment variables → Check `.env`
- Database connection refused → Verify `PGHOST` is accessible
- Port already in use → Stop conflicting service or change ports in `docker-compose.yml`

### API Returns 500 Errors

1. Check API logs: `docker compose logs scanner-api`
2. Verify database connection: `make db-shell`
3. Check Redis: `docker compose exec redis redis-cli ping`
4. Ensure all environment variables set

### Transcription Not Working

1. Check Celery logs: `docker compose logs scanner-transcription`
2. Verify Redis queue: `docker compose exec redis redis-cli LLEN celery`
3. Check MinIO audio files exist
4. Verify Whisper model downloaded (first transcription is slow)

### Frontend Not Loading

1. Check Nginx logs: `docker compose logs scanner-frontend`
2. Verify API is accessible: `curl http://localhost:8000/api/health`
3. Check browser console for errors
4. Try rebuild: `docker compose build scanner-frontend`

### Database Connection Issues

**Test connection**:
```bash
psql -h $PGHOST -U $PGUSER -d $PGDATABASE -c "SELECT 1"
```

**Common fixes**:
- Verify credentials in `.env`
- Check database is accepting connections
- Ensure security group allows your IP (if AWS RDS)

## IDE Setup

### VS Code

Recommended extensions:
- Python
- Pylance
- ESLint
- Prettier
- Docker
- GitLens

**Settings** (`.vscode/settings.json`):
```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true,
  "python.formatting.provider": "ruff",
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

### PyCharm

1. Mark directories as sources:
   - Right-click `app_api` → Mark Directory as → Sources Root
   - Repeat for other app directories
2. Configure interpreter: Docker Compose service
3. Enable Ruff: Settings → Tools → Ruff
4. Configure test runner: PyTest

## Performance Tips

### Faster Transcription
- Use smaller Whisper model: `WHISPER_MODEL=tiny` (less accurate but 5x faster)
- Reduce concurrent workers in `docker-compose.yml`

### Faster Builds
- Use BuildKit: `DOCKER_BUILDKIT=1 docker compose build`
- Cache dependencies: Don't change `requirements.txt` frequently

### Faster Database
- Use local PostgreSQL instead of remote RDS for development
- Add indexes if queries are slow (see `db/migrations/001_*.sql`)

## Next Steps

- Read [Contributing Guide](../../CONTRIBUTING.md) for code style
- Review [Architecture Documentation](../CLAUDE.md) for system design
- Check [Database Schema](../architecture/database-schema.md) for data model
- See [Deployment Checklist](../deployment/deployment-checklist.md) for production deployment

## Getting Help

- **Documentation**: Check `docs/` directory and `CLAUDE.md`
- **Logs**: Always check service logs first
- **Issues**: Search existing GitHub issues or create new one
- **Discussions**: GitHub Discussions for questions and ideas
