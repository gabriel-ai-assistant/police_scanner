"""Tests for Nominatim geocoding client."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.nominatim import NominatimClient, RateLimiter
from app.models import GeocodeRequest


class TestRateLimiter:
    """Tests for RateLimiter class."""

    @pytest.mark.asyncio
    async def test_rate_limiter_initial_request(self):
        """Test that first request goes through immediately."""
        limiter = RateLimiter(rate_per_second=10.0)
        start = asyncio.get_event_loop().time()
        await limiter.acquire()
        elapsed = asyncio.get_event_loop().time() - start
        # First request should be nearly instant
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_rate_limiter_subsequent_requests(self):
        """Test that subsequent requests are delayed."""
        limiter = RateLimiter(rate_per_second=10.0)  # 0.1 second between requests
        await limiter.acquire()
        start = asyncio.get_event_loop().time()
        await limiter.acquire()
        elapsed = asyncio.get_event_loop().time() - start
        # Second request should wait at least 0.1 seconds
        assert elapsed >= 0.09  # Allow small margin for timing


class TestNominatimClient:
    """Tests for NominatimClient class."""

    def test_make_cache_key(self):
        """Test cache key generation."""
        mock_pool = MagicMock()
        client = NominatimClient(mock_pool)

        key1 = client._make_cache_key("123 Main St", "Dallas", "TX", "United States")
        key2 = client._make_cache_key("123 main st", "dallas", "tx", "united states")
        key3 = client._make_cache_key("456 Oak Ave", "Dallas", "TX", "United States")

        # Same query with different case should produce same key
        assert key1 == key2
        # Different query should produce different key
        assert key1 != key3

    def test_parse_nominatim_response_empty(self):
        """Test parsing empty response."""
        mock_pool = MagicMock()
        client = NominatimClient(mock_pool)

        result = client._parse_nominatim_response([])
        assert result.latitude is None
        assert result.longitude is None

    def test_parse_nominatim_response_valid(self):
        """Test parsing valid response."""
        mock_pool = MagicMock()
        client = NominatimClient(mock_pool)

        response = [{
            "lat": "33.2366",
            "lon": "-96.8009",
            "importance": 0.85,
            "display_name": "123 Main Street, Prosper, TX 75078, USA",
            "address": {
                "house_number": "123",
                "road": "Main Street",
                "city": "Prosper",
                "state": "Texas",
                "postcode": "75078",
                "country": "United States"
            }
        }]

        result = client._parse_nominatim_response(response)

        assert result.latitude == 33.2366
        assert result.longitude == -96.8009
        assert result.confidence <= 1.0
        assert result.street_name == "Main Street"
        assert result.street_number == "123"
        assert result.city == "Prosper"
        assert result.state == "Texas"

    @pytest.mark.asyncio
    async def test_geocode_cache_hit(self):
        """Test that cached results are returned."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock cache hit
        mock_conn.fetchrow.return_value = {
            'latitude': 33.2366,
            'longitude': -96.8009,
            'confidence': 0.9,
            'formatted_address': '123 Main St, Prosper, TX',
            'street_name': 'Main St',
            'street_number': '123',
            'city': 'Prosper',
            'state': 'TX',
            'postal_code': '75078',
            'country': 'United States'
        }

        client = NominatimClient(mock_pool)
        request = GeocodeRequest(query="123 Main St", bias_city="Prosper", bias_state="TX")

        result = await client.geocode(request)

        assert result.cached == True
        assert result.latitude == 33.2366
        assert result.longitude == -96.8009


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
