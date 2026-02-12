"""
BUG-025/026/027: Docker Compose services missing postgres dependency.

Tests that app_api, app_scheduler, and app_transcription depend on
postgres with condition: service_healthy.
"""

import os

import pytest
import yaml

COMPOSE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "docker-compose.yml"
)


@pytest.fixture
def compose_config():
    """Load docker-compose.yml."""
    with open(COMPOSE_PATH) as f:
        return yaml.safe_load(f)


class TestDockerComposeDependencies:
    """BUG-025/026/027: Services must depend on postgres with healthcheck."""

    def test_postgres_has_healthcheck(self, compose_config):
        """postgres service must have a healthcheck defined."""
        postgres = compose_config["services"]["postgres"]
        assert "healthcheck" in postgres, "postgres missing healthcheck"
        assert "test" in postgres["healthcheck"], "postgres healthcheck missing test command"

    def test_app_api_depends_on_postgres(self, compose_config):
        """app_api must depend on postgres with service_healthy condition."""
        deps = compose_config["services"]["app_api"]["depends_on"]
        assert "postgres" in deps, "app_api missing postgres dependency"
        assert deps["postgres"]["condition"] == "service_healthy", \
            "app_api postgres dependency should use service_healthy condition"

    def test_app_scheduler_depends_on_postgres(self, compose_config):
        """app_scheduler must depend on postgres with service_healthy condition."""
        deps = compose_config["services"]["app_scheduler"]["depends_on"]
        assert "postgres" in deps, "app_scheduler missing postgres dependency"
        assert deps["postgres"]["condition"] == "service_healthy", \
            "app_scheduler postgres dependency should use service_healthy condition"

    def test_app_transcription_depends_on_postgres(self, compose_config):
        """app_transcription must depend on postgres with service_healthy condition."""
        deps = compose_config["services"]["app_transcription"]["depends_on"]
        assert "postgres" in deps, "app_transcription missing postgres dependency"
        assert deps["postgres"]["condition"] == "service_healthy", \
            "app_transcription postgres dependency should use service_healthy condition"
