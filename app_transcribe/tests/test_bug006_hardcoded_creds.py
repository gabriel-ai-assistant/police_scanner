"""
BUG-006: Hardcoded database credentials in transcribe_audio.py.

Tests that DB config uses os.getenv() for all fields and doesn't
contain hardcoded passwords/usernames.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestHardcodedCreds:
    """BUG-006: DB credentials must come from environment variables."""

    def test_db_password_not_hardcoded(self):
        """DB password must not be a hardcoded string."""
        # We need to check the source since the module executes on import
        source_path = os.path.join(os.path.dirname(__file__), "..", "transcribe_audio.py")
        with open(source_path) as f:
            source = f.read()

        # Should not have hardcoded password value "scanner"
        # Check for the pattern: "password": "scanner"
        assert '"password": "scanner"' not in source, \
            "DB password is hardcoded as 'scanner'"

    def test_db_user_uses_env(self):
        """DB user must use os.getenv()."""
        source_path = os.path.join(os.path.dirname(__file__), "..", "transcribe_audio.py")
        with open(source_path) as f:
            source = f.read()

        assert '"user": "scanner"' not in source, \
            "DB user is hardcoded as 'scanner'"

    def test_db_config_uses_pguser_env(self):
        """DB config should reference PGUSER environment variable."""
        source_path = os.path.join(os.path.dirname(__file__), "..", "transcribe_audio.py")
        with open(source_path) as f:
            source = f.read()

        assert "PGUSER" in source, "Should use PGUSER env var"
        assert "PGPASSWORD" in source, "Should use PGPASSWORD env var"
        assert "PGHOST" in source, "Should use PGHOST env var"
        assert "PGDATABASE" in source, "Should use PGDATABASE env var"
        assert "PGPORT" in source, "Should use PGPORT env var"

    def test_db_port_uses_env(self):
        """DB port must use os.getenv(), not hardcoded '5432' only."""
        source_path = os.path.join(os.path.dirname(__file__), "..", "transcribe_audio.py")
        with open(source_path) as f:
            source = f.read()

        # Port should reference env var (can have "5432" as default, that's fine)
        assert '"port": "5432"' not in source or "getenv" in source, \
            "DB port should use os.getenv()"

    def test_all_db_fields_use_getenv(self):
        """Every field in the DB dict should call os.getenv()."""
        source_path = os.path.join(os.path.dirname(__file__), "..", "transcribe_audio.py")
        with open(source_path) as f:
            source = f.read()

        # Find the DB = { ... } block and count getenv calls
        # All 5 fields (host, port, dbname, user, password) should use getenv
        db_block_start = source.index("DB = {")
        db_block_end = source.index("}", db_block_start) + 1
        db_block = source[db_block_start:db_block_end]

        getenv_count = db_block.count("os.getenv")
        assert getenv_count >= 5, \
            f"Expected at least 5 os.getenv() calls in DB config, found {getenv_count}"
