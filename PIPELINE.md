# CI/CD Pipeline

## Branch Strategy

```
feature/* → develop → staging → main
              ↓          ↓         ↓
           aidev01     aiqa01   tag/release
          (10.69.69.9) (10.69.69.10)
```

## Flow

### 1. Feature Development
- Create `feature/*` branch from `develop`
- Open PR to `develop` — triggers **CI** (lint, tests, docker build check)
- Merge after review + CI green

### 2. Dev Deploy (`develop` branch)
- Push/merge to `develop` → CI runs → on success, **deploy-dev.yml** triggers
- SSHs into **aidev01** (10.69.69.9, user gabriel)
- Pulls latest, `docker compose build && up -d`
- Runs `scripts/smoke-test.sh` (health + frontend check)

### 3. Staging Deploy (`staging` branch)
- Merge `develop` → `staging` → CI runs → on success, **deploy-staging.yml** triggers
- SSHs into **aiqa01** (10.69.69.10, user gabriel)
- Pulls latest, `docker compose build && up -d`
- Runs **full staging test gate** (`scripts/staging-tests.sh`):
  - API health & all core endpoints (authenticated)
  - Auth flow (login → token → protected access)
  - Security checks (401 without auth)
  - Performance baseline (<2s response times)
  - Docker container health (all up/healthy)
  - DB migration success
  - Frontend serves valid HTML

### 4. Promote to Main
- Open PR from `staging` → `main` → **promote-to-main.yml** triggers
- Validates source is `staging` branch
- Checks latest staging deployment succeeded
- Runs full test suite one more time
- On merge: auto-tags with semver (patch bump), triggers `docker-build.yml`

## GitHub Secrets Required

| Secret | Used By | Description |
|--------|---------|-------------|
| `DEV_SSH_KEY` | deploy-dev.yml | SSH private key for gabriel@10.69.69.9 |
| `QA_SSH_KEY` | deploy-staging.yml, promote-to-main.yml | SSH private key for gabriel@10.69.69.10 |

## Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push/PR to develop, staging, main | Lint, test, docker build check |
| `deploy-dev.yml` | CI passes on develop | Deploy to aidev01 + smoke test |
| `deploy-staging.yml` | CI passes on staging | Deploy to aiqa01 + full test gate |
| `promote-to-main.yml` | PR to main from staging | Final gate + tag + release |
| `docker-build.yml` | Version tags (`v*`) | Build & push images to GHCR |
