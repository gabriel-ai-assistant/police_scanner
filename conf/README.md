# Configuration Directory

This directory contains configuration templates and utility scripts for the Police Scanner Analytics Platform.

## Files

### config.yaml.example
**Purpose**: Legacy configuration template from earlier version of the system

**Status**: Not currently used by the Docker-based deployment

**Description**: This file contains configuration for an older version of the scanner system that used YAML configuration instead of environment variables. It includes:
- Broadcastify cookie authentication (now replaced by JWT API keys)
- Session management
- Signal notification settings
- Whisper configuration

**Note**: The current Docker Compose deployment uses `.env` files for configuration (see `../.env.example` at project root). This file is preserved for reference and potential future use.

---

### meili_create_index.sh
**Purpose**: Create MeiliSearch index for transcripts

**Usage**:
```bash
# Set environment variables first
export MEILI_HOST=http://localhost:7700
export MEILI_MASTER_KEY=your-master-key

# Run script
bash conf/meili_create_index.sh
```

**Description**: Creates the `transcripts` index in MeiliSearch. This script is idempotent (safe to run multiple times). The index is automatically created when the application starts, so this script is mainly useful for:
- Manual index creation/recreation
- Troubleshooting search issues
- Development/testing environments

**Note**: The application automatically creates indexes on startup, so running this script manually is usually not necessary.

---

## Migration Notes

### From Legacy System to Current Docker Deployment

The platform has evolved from a single-process YAML-configured system to a distributed Docker Compose microservices architecture:

**Old System** (config.yaml):
- Single Python script (`download_calls.py`)
- YAML configuration
- Cookie-based authentication
- Local file storage
- Signal notifications

**Current System** (.env + Docker Compose):
- Microservices architecture (API, Scheduler, Transcription)
- Environment variable configuration
- JWT API authentication
- S3/MinIO object storage
- Database-backed state management

### If You Need Cookie Authentication

The current system uses Broadcastify's official API with JWT tokens (configured via environment variables in `.env`). If you need the old cookie-based approach:

1. Refer to `config.yaml.example` for cookie structure
2. Update authentication in `shared_bcfy/auth.py`
3. Modify `app_scheduler/get_calls.py` to use cookies instead of JWT

However, **JWT API access is strongly recommended** as it's:
- More secure
- Officially supported by Broadcastify
- More reliable (no cookie expiration issues)

---

## Environment Configuration

For current deployments, use the main `.env` file at project root:

```bash
# Root directory
/opt/policescanner/.env          # Production configuration
/opt/policescanner/.env.example  # Template
```

Required environment variables:
- Database: `PGHOST`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`
- Broadcastify: `BCFY_API_KEY`, `BCFY_API_KEY_ID`, `BCFY_APP_ID`
- Storage: `MINIO_ENDPOINT`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`
- Search: `MEILI_HOST`, `MEILI_MASTER_KEY`

See main [README.md](../README.md) and [.env.example](../.env.example) for complete documentation.

---

## Additional Resources

- **Architecture**: See [CLAUDE.md](../CLAUDE.md)
- **Deployment**: See [docs/deployment/](../docs/deployment/)
- **Development**: See [docs/guides/local-development.md](../docs/guides/local-development.md)

---

**Last Updated**: 2025-12-12
