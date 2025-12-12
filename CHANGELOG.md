# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-12

### Added

#### Repository Organization & Professional Polish
- **Documentation Structure**: Created `docs/` directory with subdirectories for deployment, architecture, and guides
- **Standard Project Files**: Added README.md, LICENSE, CONTRIBUTING.md, and CHANGELOG.md
- **Build Automation**: Created Makefile with common development tasks
- **Code Quality Configs**: Added .editorconfig, Prettier, ESLint, and Ruff configurations
- **CI/CD**: Implemented GitHub Actions workflows for testing and Docker builds
- **GitHub Templates**: Added issue templates (bug report, feature request) and PR template

#### Directory Structure Improvements
- **Test Organization**: Moved all test files to dedicated `tests/` directories in each service
  - `app_api/tests/`
  - `app_scheduler/tests/`
  - `app_transcribe/tests/`
  - `shared_bcfy/tests/`
- **Script Organization**: Created `scripts/` directory for build and deployment automation
  - `scripts/deploy.sh`
  - `scripts/setup-dev.sh`
  - `scripts/run-tests.sh`
- **Database Scripts**: Moved execution scripts to `db/scripts/` directory

#### Documentation Enhancements
- **README.md**: Comprehensive project overview with architecture diagrams, quick start guide, and API documentation links
- **CONTRIBUTING.md**: Detailed development guidelines including code style, git workflow, and testing requirements
- **Architecture Decision**: Documented rationale for microservices-at-root structure (vs src/ monorepo style)
- **Documentation Index**: Created `docs/README.md` as navigation hub
- **Local Development Guide**: Added `docs/guides/local-development.md` for developer onboarding
- **Production Checklist**: Created `docs/deployment/production-checklist.md`

### Changed

#### File Reorganization
- **Documentation**: Moved markdown files from root to `docs/` subdirectories
  - `IMPLEMENTATION_SUMMARY.md` → `docs/guides/implementation-summary.md`
  - `DEPLOYMENT_CHECKLIST.md` → `docs/deployment/deployment-checklist.md`
  - `AUDIO_ENHANCEMENT_DEPLOYMENT.md` → `docs/deployment/audio-enhancement.md`
- **Tests**: Reorganized test files into proper test directories with `__init__.py` files
  - `app_scheduler/test_*.py` → `app_scheduler/tests/test_*.py`
  - Renamed `regression_test_ingestion.py` → `test_regression_ingestion.py` for consistency

#### Git Configuration
- **.gitignore**: Comprehensively updated with patterns for:
  - Temporary audio files (`shared_bcfy/tmp/` - prevents 2MB+ of MP3s from being committed)
  - IDE files (`.idea/`, `.vscode/`, vim swap files)
  - Database backups (`*.backup`, `db/backups/`)
  - Build artifacts (`dist/`, `build/`, `.cache/`)
  - Testing artifacts (`.pytest_cache/`, `.coverage`, `htmlcov/`)
  - Python packaging files (`*.egg-info/`, `.mypy_cache/`, `.ruff_cache/`)
  - OS files (`.DS_Store`, `Thumbs.db`)
  - Environment overrides (`.env.local`, `.env.*.local`)

### Removed
- **Temporary Files**: Deleted 91+ MP3 audio files from `shared_bcfy/tmp/` (2MB+ of uncommitted media)
- **Obsolete Files**: Removed `frontend/package.json.new`, `db/init.sql.backup.20251210`, `db/IMPLEMENTATION_READY.txt`

### Fixed
- **Security**: Verified `.env` file was never committed to git history (no credential leaks)
- **File Organization**: Eliminated root-level clutter by moving files to appropriate subdirectories

### Infrastructure
- **Environment Template**: Created `.env.example` with sanitized placeholder values for all required environment variables
- **Code Quality**: Configured Ruff (Python), ESLint (TypeScript), and Prettier (frontend) for consistent code formatting
- **Docker**: Verified all service configurations remain compatible with reorganized file structure

---

## Historical Notes

This changelog was created as part of the v1.0.0 repository reorganization. For changes prior to this reorganization, consult git commit history.

### Architectural Decisions

**Microservices at Root Level**: Services (`app_api/`, `app_scheduler/`, `app_transcribe/`, `frontend/`) remain at root level following Docker Compose microservices best practices. This structure:
- Makes service boundaries immediately visible
- Simplifies Docker volume mounts
- Allows independent service deployment
- Follows industry standards (Airflow, Temporal, Kong)

See [CLAUDE.md](CLAUDE.md) for detailed architecture documentation.

---

[1.0.0]: https://github.com/yourorg/policescanner/releases/tag/v1.0.0
