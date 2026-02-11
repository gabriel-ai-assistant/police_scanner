"""
Tests for docker-compose.yml service dependencies.
BUG-025/026/027: Services must depend on postgres.
"""
import os
import pytest
import yaml

COMPOSE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "docker-compose.yml")


@pytest.fixture
def compose_services():
    with open(COMPOSE_PATH) as f:
        data = yaml.safe_load(f)
    return data.get("services", {})


class TestBUG025_026_027DockerDependencies:
    """app_api, app_scheduler, and app_transcription must depend on postgres."""

    def _get_depends(self, services, name):
        svc = services.get(name, {})
        deps = svc.get("depends_on", {})
        if isinstance(deps, list):
            return deps
        elif isinstance(deps, dict):
            return list(deps.keys())
        return []

    def test_app_api_depends_on_postgres(self, compose_services):
        deps = self._get_depends(compose_services, "app_api")
        assert "postgres" in deps, \
            f"app_api depends_on={deps}, missing 'postgres'"

    def test_app_scheduler_depends_on_postgres(self, compose_services):
        deps = self._get_depends(compose_services, "app_scheduler")
        assert "postgres" in deps, \
            f"app_scheduler depends_on={deps}, missing 'postgres'"

    def test_app_transcription_depends_on_postgres(self, compose_services):
        # Try both possible service names
        deps = self._get_depends(compose_services, "app_transcription")
        if not deps:
            deps = self._get_depends(compose_services, "app_transcribe")
        assert "postgres" in deps, \
            f"app_transcription depends_on={deps}, missing 'postgres'"
