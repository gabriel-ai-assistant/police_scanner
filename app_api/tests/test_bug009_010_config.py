"""
BUG-009: Hardcoded MinIO IP address in config.py.
BUG-010: SESSION_COOKIE_SECURE defaults to False.

Tests that config defaults are safe for production.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestConfigDefaults:
    """BUG-009/010: Config defaults must be production-safe."""

    def test_minio_endpoint_not_hardcoded_ip(self):
        """MINIO_ENDPOINT default must not be a private IP address."""
        source_path = os.path.join(os.path.dirname(__file__), "..", "config.py")
        with open(source_path) as f:
            source = f.read()

        assert "192.168." not in source, \
            "MINIO_ENDPOINT still contains hardcoded private IP"
        assert "10.0." not in source, \
            "MINIO_ENDPOINT contains hardcoded private IP"

    def test_minio_endpoint_uses_service_name(self):
        """MINIO_ENDPOINT should default to Docker service name."""
        source_path = os.path.join(os.path.dirname(__file__), "..", "config.py")
        with open(source_path) as f:
            source = f.read()

        assert "minio:9000" in source, \
            "MINIO_ENDPOINT should default to 'minio:9000'"

    def test_session_cookie_secure_defaults_true(self):
        """SESSION_COOKIE_SECURE must default to True for production safety."""
        source_path = os.path.join(os.path.dirname(__file__), "..", "config.py")
        with open(source_path) as f:
            source = f.read()

        # Find the SESSION_COOKIE_SECURE line
        for line in source.split('\n'):
            if 'SESSION_COOKIE_SECURE' in line and 'bool' in line:
                assert 'True' in line, \
                    f"SESSION_COOKIE_SECURE should default to True, found: {line.strip()}"
                assert 'False' not in line, \
                    f"SESSION_COOKIE_SECURE must not default to False"
                break
        else:
            pytest.fail("SESSION_COOKIE_SECURE field not found in config")

    def test_config_can_be_instantiated_with_required_env(self, monkeypatch):
        """Settings should instantiate when required env vars are set."""
        monkeypatch.setenv("PGPASSWORD", "test")
        monkeypatch.setenv("MINIO_ROOT_PASSWORD", "test")

        # Re-import to pick up monkeypatched env
        from importlib import reload
        import config
        reload(config)

        assert config.settings.SESSION_COOKIE_SECURE is True
        assert config.settings.MINIO_ENDPOINT == "minio:9000"
