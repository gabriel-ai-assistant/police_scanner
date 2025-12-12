# Production Deployment Checklist

Complete pre-deployment verification checklist for production deployment of the Police Scanner Analytics Platform.

## Pre-Deployment Verification

### Code & Version Control

- [ ] All code merged to `main` branch
- [ ] All tests passing in CI/CD
- [ ] No uncommitted changes in working directory
- [ ] Version tag created (e.g., `v1.0.0`)
- [ ] CHANGELOG.md updated with release notes
- [ ] Code reviewed and approved by team

### Environment Configuration

- [ ] `.env` file configured with production credentials
- [ ] All required environment variables set:
  - [ ] Database credentials (`PGHOST`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`)
  - [ ] Broadcastify API keys (`BCFY_API_KEY`, `BCFY_API_KEY_ID`, `BCFY_APP_ID`)
  - [ ] MinIO/S3 credentials (`MINIO_ENDPOINT`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`)
  - [ ] MeiliSearch master key (`MEILI_MASTER_KEY`)
  - [ ] OpenAI API key if using cloud Whisper (`OPENAI_API_KEY`)
  - [ ] CORS origins set correctly (`CORS_ORIGINS`)
  - [ ] Log level appropriate for production (`LOG_LEVEL=INFO`)
- [ ] No development/debug settings enabled
- [ ] API rate limits configured appropriately

### Infrastructure

**Database (PostgreSQL)**:
- [ ] Database accessible from deployment environment
- [ ] Database backups configured and tested
- [ ] Connection pooling limits set appropriately
- [ ] Performance monitoring enabled
- [ ] Sufficient disk space allocated

**Redis**:
- [ ] Redis accessible and persistent
- [ ] Memory limits configured
- [ ] Eviction policy set
- [ ] Monitoring enabled

**MinIO/S3 Storage**:
- [ ] Bucket created and accessible
- [ ] Lifecycle policies configured (optional: auto-delete old audio)
- [ ] Sufficient storage capacity
- [ ] Backup/replication configured

**MeiliSearch**:
- [ ] Index created
- [ ] Master key set (production-strong)
- [ ] Sufficient disk space
- [ ] Dump/snapshot backup configured

### Database Migrations

- [ ] All migration files tested on copy of production data
- [ ] Migration order verified (sequential)
- [ ] Rollback scripts prepared
- [ ] Database backed up before migration
- [ ] Migrations executed successfully:
  ```bash
  python db/scripts/execute-migrations.py
  ```
- [ ] Post-migration validation queries run:
  ```sql
  -- Verify table counts
  SELECT COUNT(*) FROM bcfy_calls_raw;
  SELECT COUNT(*) FROM transcripts;

  -- Verify indexes exist
  SELECT tablename, indexname FROM pg_indexes
  WHERE schemaname = 'public'
  ORDER BY tablename, indexname;
  ```

### Security

- [ ] All secrets rotated and stored securely
- [ ] No hardcoded credentials in code
- [ ] `.env` file not committed to git
- [ ] SSL/TLS enabled for all external connections
- [ ] Database connection encrypted
- [ ] Firewall rules configured (only necessary ports open)
- [ ] Security groups/network policies configured
- [ ] API rate limiting enabled
- [ ] CORS configured for production domains only
- [ ] No debug endpoints exposed

### Docker & Containers

- [ ] All Docker images built successfully:
  ```bash
  docker compose build --no-cache
  ```
- [ ] Images scanned for vulnerabilities
- [ ] Resource limits set in `docker-compose.yml`:
  - [ ] Memory limits
  - [ ] CPU limits
  - [ ] Restart policies (`restart: unless-stopped`)
- [ ] Healthchecks defined for all services
- [ ] Logging drivers configured
- [ ] Volumes properly configured for persistence

### Application Configuration

**API Service**:
- [ ] Correct API host and port (`API_HOST`, `API_PORT`)
- [ ] CORS origins set to production domains
- [ ] Cache TTLs appropriate for production load
- [ ] Database connection pool sized correctly (5-20 connections)
- [ ] Timeout values set appropriately

**Scheduler Service**:
- [ ] Polling intervals configured (`BCFY_REFRESH_CALLS_MINUTES`)
- [ ] Geographic filters set if needed (`BCFY_COUNTRY_CODES`, `BCFY_STATE_CODES`)
- [ ] Feed refresh intervals appropriate

**Transcription Service**:
- [ ] Whisper model size appropriate (`WHISPER_MODEL=small` recommended)
- [ ] Celery worker count set (`--concurrency` in Dockerfile)
- [ ] Audio processing timeouts configured
- [ ] Queue monitoring enabled

**Frontend**:
- [ ] Production build created (`npm run build`)
- [ ] Static assets cached properly (Nginx configuration)
- [ ] Environment-specific API endpoints set

### Testing

- [ ] All unit tests pass:
  ```bash
  pytest app_api/tests/ app_scheduler/tests/ app_transcribe/tests/ -v
  ```
- [ ] All frontend tests pass:
  ```bash
  cd frontend && npm test
  ```
- [ ] Integration tests pass
- [ ] Load testing performed (if applicable)
- [ ] Manual smoke tests completed:
  - [ ] API health check: `curl http://localhost:8000/api/health`
  - [ ] Frontend loads correctly
  - [ ] New calls are being ingested
  - [ ] Transcription pipeline working
  - [ ] Search functionality works

### Monitoring & Logging

- [ ] Application logs collected centrally
- [ ] Log retention policy configured
- [ ] Error tracking enabled (Sentry, Rollbar, etc.)
- [ ] Performance monitoring enabled (APM tool)
- [ ] Metrics collection configured:
  - [ ] API response times
  - [ ] Database query performance
  - [ ] Transcription queue length
  - [ ] Error rates
- [ ] Alerts configured for:
  - [ ] Service downtime
  - [ ] High error rates
  - [ ] Database connection failures
  - [ ] Queue backlog
  - [ ] Disk space warnings
- [ ] Dashboard created for key metrics

### Backup & Recovery

- [ ] Database backup strategy defined and automated
- [ ] Backup retention policy defined (e.g., 30 days)
- [ ] Backup restoration tested successfully
- [ ] MinIO/S3 backup or replication configured
- [ ] Disaster recovery plan documented
- [ ] Recovery time objective (RTO) defined
- [ ] Recovery point objective (RPO) defined

### Documentation

- [ ] Production environment variables documented
- [ ] Deployment procedure documented
- [ ] Rollback procedure documented
- [ ] Troubleshooting guide updated
- [ ] Contact information for on-call team
- [ ] Runbook created for common issues

## Deployment Execution

### Step 1: Pre-Deployment Verification

```bash
# Verify git status
git status
git log -1

# Run tests
make test

# Build containers
docker compose build
```

### Step 2: Database Migration

```bash
# Backup database first!
make db-backup

# Run migrations
python db/scripts/execute-migrations.py

# Verify migrations
psql -h $PGHOST -U $PGUSER -d $PGDATABASE -c "\dt"
```

### Step 3: Deploy Application

```bash
# Stop current services
docker compose down

# Pull latest code (if deploying from git)
git pull origin main

# Start new services
docker compose up -d

# Wait for services to initialize
sleep 15
```

### Step 4: Post-Deployment Verification

```bash
# Check service health
make health

# Check logs for errors
docker compose logs --tail=100

# Verify each service
curl http://localhost:8000/api/health  # API
curl http://localhost:7700/health      # MeiliSearch
curl http://localhost:80               # Frontend
```

### Step 5: Monitoring

```bash
# Monitor logs
docker compose logs -f

# Check resource usage
docker stats

# Watch for errors in database
# Watch for queue backlog in Redis
```

## Post-Deployment Checklist

- [ ] All services healthy and running
- [ ] Health check endpoints return 200 OK
- [ ] No errors in application logs
- [ ] Database connections stable
- [ ] Transcription pipeline processing calls
- [ ] Search functionality working
- [ ] Frontend accessible and functioning
- [ ] No spike in error rates
- [ ] Performance within acceptable ranges
- [ ] Monitoring dashboards showing green
- [ ] Team notified of successful deployment

## Rollback Procedure

If deployment fails or critical issues arise:

### Step 1: Stop New Services
```bash
docker compose down
```

### Step 2: Restore Database (if needed)
```bash
psql -h $PGHOST -U $PGUSER -d $PGDATABASE < db/backups/backup_YYYYMMDD_HHMMSS.sql
```

### Step 3: Revert Code
```bash
git checkout <previous-tag>
```

### Step 4: Rebuild and Start
```bash
docker compose build
docker compose up -d
```

### Step 5: Verify Rollback
```bash
make health
docker compose logs --tail=100
```

## Emergency Contacts

- **On-Call Engineer**: [Contact info]
- **Database Administrator**: [Contact info]
- **DevOps Team**: [Contact info]
- **Escalation Path**: [Escalation procedure]

## Additional Resources

- [Deployment Guide](deployment-checklist.md)
- [Architecture Documentation](../CLAUDE.md)
- [Troubleshooting Guide](../CLAUDE.md#troubleshooting)
- [Database Schema](../architecture/database-schema.md)

---

**Last Updated**: 2025-12-12
**Checklist Version**: 1.0
