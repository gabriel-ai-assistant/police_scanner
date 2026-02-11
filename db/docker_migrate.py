#!/usr/bin/env python3
"""
Docker Migration Runner

Applies init.sql (idempotent base schema) and then each numbered migration
in order.  Tracks applied migrations in a `schema_migrations` table so
migrations are never re-run.

Environment variables (all optional, with sensible defaults for the
docker-compose stack):
    PGHOST      – default "postgres"
    PGPORT      – default "5432"
    PGUSER      – default "scan"
    PGPASSWORD  – required (no default)
    PGDATABASE  – default "scanner"
"""

import glob
import os
import re
import subprocess
import sys
import time

PGHOST = os.getenv("PGHOST", "postgres")
PGPORT = os.getenv("PGPORT", "5432")
PGUSER = os.getenv("PGUSER", "scan")
PGPASSWORD = os.getenv("PGPASSWORD", "")
PGDATABASE = os.getenv("PGDATABASE", "scanner")

if not PGPASSWORD:
    print("ERROR: PGPASSWORD environment variable is empty or unset.", file=sys.stderr, flush=True)
    sys.exit(1)

MIGRATIONS_DIR = "/app/migrations"
INIT_SQL = "/app/init.sql"

# Maximum time to wait for postgres to accept connections (seconds)
MAX_WAIT = 60


def _validate_version(version: str) -> None:
    """Ensure version is safe for SQL use (digits only, or literal 'init')."""
    if version != "init" and not re.fullmatch(r"\d+", version):
        raise ValueError(f"Invalid migration version (must be digits only): {version!r}")


def psql(*args: str, file: str | None = None, single_transaction: bool = False) -> int:
    """Run a psql command and return the exit code."""
    env = {
        **os.environ,
        "PGHOST": PGHOST,
        "PGPORT": PGPORT,
        "PGUSER": PGUSER,
        "PGPASSWORD": PGPASSWORD,
        "PGDATABASE": PGDATABASE,
    }
    cmd = ["psql", "-v", "ON_ERROR_STOP=1", *args]
    if single_transaction:
        cmd.insert(1, "-1")
    if file:
        cmd.extend(["-f", file])
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        # psql prints NOTICE/INFO to stderr; only flag actual errors
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


def wait_for_postgres() -> None:
    """Block until postgres accepts connections or MAX_WAIT is exceeded."""
    print(f"Waiting for postgres at {PGHOST}:{PGPORT} ...", flush=True)
    env = {
        **os.environ,
        "PGHOST": PGHOST,
        "PGPORT": PGPORT,
        "PGUSER": PGUSER,
        "PGPASSWORD": PGPASSWORD,
        "PGDATABASE": PGDATABASE,
    }
    deadline = time.time() + MAX_WAIT
    while time.time() < deadline:
        ret = subprocess.run(
            ["pg_isready", "-h", PGHOST, "-p", PGPORT, "-U", PGUSER],
            env=env,
            capture_output=True,
        )
        if ret.returncode == 0:
            print("Postgres is ready.", flush=True)
            return
        time.sleep(1)
    print("ERROR: Postgres did not become ready in time.", file=sys.stderr, flush=True)
    sys.exit(1)


def ensure_tracking_table() -> None:
    """Create the schema_migrations tracking table if it doesn't exist."""
    sql = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version TEXT PRIMARY KEY,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """
    rc = psql("-c", sql)
    if rc != 0:
        print("ERROR: Could not create schema_migrations table.", file=sys.stderr)
        sys.exit(1)


def already_applied(version: str) -> bool:
    """Check whether a migration version has been recorded."""
    _validate_version(version)
    env = {
        **os.environ,
        "PGHOST": PGHOST,
        "PGPORT": PGPORT,
        "PGUSER": PGUSER,
        "PGPASSWORD": PGPASSWORD,
        "PGDATABASE": PGDATABASE,
    }
    # Use psql variable binding to avoid SQL injection
    result = subprocess.run(
        [
            "psql",
            "-tAc",
            "SELECT 1 FROM schema_migrations WHERE version = :'mig_version';",
            "-v", f"mig_version={version}",
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == "1"


def record_migration(version: str) -> None:
    """Record a migration as applied."""
    _validate_version(version)
    psql(
        "-c",
        "INSERT INTO schema_migrations (version) VALUES (:'mig_version');",
        "-v", f"mig_version={version}",
    )


def apply_init_sql() -> None:
    """Apply the base schema (init.sql) if it hasn't been applied yet."""
    version = "init"
    if already_applied(version):
        print("init.sql already applied – skipping.", flush=True)
        return
    if not os.path.exists(INIT_SQL):
        print("No init.sql found – skipping base schema.", flush=True)
        return
    print("Applying init.sql (base schema) ...", flush=True)
    rc = psql(file=INIT_SQL, single_transaction=True)
    if rc != 0:
        print("ERROR: init.sql failed.", file=sys.stderr)
        sys.exit(1)
    record_migration(version)
    print("init.sql applied successfully.", flush=True)


def discover_migrations() -> list[tuple[str, str]]:
    """Return sorted list of (version, filepath) for SQL migrations."""
    pattern = os.path.join(MIGRATIONS_DIR, "*.sql")
    files = sorted(glob.glob(pattern))
    migrations: list[tuple[str, str]] = []
    for filepath in files:
        basename = os.path.basename(filepath)
        # Extract leading number: 001_foo.sql -> "001"
        match = re.match(r"^(\d+)", basename)
        if match:
            migrations.append((match.group(1), filepath))
    return migrations


def run_migrations() -> None:
    """Apply each pending migration in order."""
    migrations = discover_migrations()
    if not migrations:
        print("No migration files found.", flush=True)
        return

    applied = 0
    skipped = 0
    for version, filepath in migrations:
        name = os.path.basename(filepath)
        if already_applied(version):
            skipped += 1
            continue
        print(f"Applying migration {name} ...", flush=True)
        rc = psql(file=filepath, single_transaction=True)
        if rc != 0:
            print(f"ERROR: Migration {name} failed.", file=sys.stderr)
            sys.exit(1)
        record_migration(version)
        applied += 1
        print(f"Migration {name} applied successfully.", flush=True)

    print(f"\nMigration summary: {applied} applied, {skipped} already up-to-date.", flush=True)


def main() -> None:
    wait_for_postgres()
    ensure_tracking_table()
    apply_init_sql()
    run_migrations()
    print("\nAll migrations complete. Exiting.", flush=True)


if __name__ == "__main__":
    main()
