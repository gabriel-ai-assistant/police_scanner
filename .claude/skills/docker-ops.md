---
name: "Docker Operations"
description: "Manage Docker Compose services and troubleshoot containers"
---

## Context

Use this skill when managing Docker Compose services for the Police Scanner platform. This includes starting/stopping services, debugging container issues, and rebuilding images.

## Scope

Files this agent works with:
- `docker-compose.yml` - Service orchestration
- `app_api/Dockerfile` - API image
- `app_scheduler/Dockerfile` - Scheduler image
- `app_transcribe/Dockerfile` - Transcription worker image
- `frontend/Dockerfile` - Frontend image (multi-stage)
- `frontend/nginx.conf` - Nginx configuration

## Instructions

When invoked, follow these steps:

1. **Understand the task**
   - Identify which service(s) need attention
   - Check current container status: `docker compose ps`
   - Review health check status if applicable

2. **Diagnose issues**
   - Check container logs for errors
   - Verify environment variables are set
   - Check service dependencies

3. **Take action**
   - Restart, rebuild, or reconfigure as needed
   - Use targeted rebuilds for specific services
   - Verify health checks pass after changes

4. **Verify**
   - Confirm services are healthy
   - Test endpoint connectivity
   - Check logs for startup errors

## Behaviors

- Use `docker compose` commands (not legacy `docker-compose`)
- Check container logs before diagnosing issues
- Verify health check endpoints respond
- Use `docker compose exec` for container shell access
- Rebuild specific services when code changes
- Use `--no-cache` only when necessary

## Constraints

- Never run `docker compose down -v` without confirmation (destroys volumes)
- Never modify running containers directly (use config files)
- Never expose internal ports unnecessarily
- Never use `--force` flags without understanding impact
- Never skip health check verification after restarts

## Safety Checks

Before completing:
- [ ] Service dependencies verified before restart
- [ ] Disk space checked before builds
- [ ] Environment variables confirmed set
- [ ] Health checks passing after changes
- [ ] No orphaned containers left running

## Common Commands

```bash
# Check status
docker compose ps

# View logs
docker compose logs --tail=100 <service>

# Restart service
docker compose restart <service>

# Rebuild and restart
docker compose build <service> && docker compose up -d <service>

# Rebuild without cache
docker compose build --no-cache <service>

# Shell access
docker compose exec <service> bash

# Stop all
docker compose down

# Stop with volume cleanup (DANGEROUS)
docker compose down -v
```

## Service Reference

| Service | Container | Port | Health Check |
|---------|-----------|------|--------------|
| scanner-api | scanner-api | 8000 | GET /api/health |
| frontend | scanner-frontend | 80 | GET /health |
| scanner-transcription | scanner-transcription | - | None |
| app-scheduler | app-scheduler | - | None |
| redis | redis | 6379 | None |
| meilisearch | meilisearch | 7700 | GET /health |

## Troubleshooting

```bash
# Container won't start - check logs
docker compose logs <service>

# Health check failing - verify endpoint
curl http://localhost:8000/api/health

# Out of disk space
docker system df
docker system prune -a

# Orphaned containers
docker compose down --remove-orphans

# Network issues
docker network ls
docker network inspect policescanner_default
```
