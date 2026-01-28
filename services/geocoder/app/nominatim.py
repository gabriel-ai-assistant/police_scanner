"""
Nominatim OpenStreetMap Geocoding Client.

Rate limited to 1 request per second per OSM policy.
"""
import asyncio
import hashlib
import logging
from typing import Optional
from datetime import datetime, timezone

import httpx
import asyncpg

from app.config import settings
from app.models import GeocodeRequest, GeocodeResult

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, rate_per_second: float = 1.0):
        self.rate = rate_per_second
        self.last_request: Optional[float] = None
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait until we can make a request."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            if self.last_request is not None:
                elapsed = now - self.last_request
                min_interval = 1.0 / self.rate
                if elapsed < min_interval:
                    await asyncio.sleep(min_interval - elapsed)
            self.last_request = asyncio.get_event_loop().time()


class NominatimClient:
    """Client for OpenStreetMap Nominatim geocoding API."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.rate_limiter = RateLimiter(settings.GEOCODE_RATE_LIMIT)
        self.base_url = settings.NOMINATIM_URL
        self.user_agent = settings.NOMINATIM_USER_AGENT

    def _make_cache_key(self, query: str, bias_city: Optional[str],
                        bias_state: Optional[str], bias_country: str) -> str:
        """Create a cache key hash for the query."""
        normalized = f"{query.lower().strip()}|{(bias_city or '').lower()}|{(bias_state or '').lower()}|{bias_country.lower()}"
        return hashlib.sha256(normalized.encode()).hexdigest()

    async def _check_cache(self, query_hash: str) -> Optional[GeocodeResult]:
        """Check if we have a cached result."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                UPDATE geocode_cache
                SET hit_count = hit_count + 1, last_hit_at = NOW()
                WHERE query_hash = $1 AND expires_at > NOW()
                RETURNING latitude, longitude, confidence, formatted_address,
                          street_name, street_number, city, state, postal_code, country
            """, query_hash)

            if row:
                return GeocodeResult(
                    latitude=float(row['latitude']) if row['latitude'] else None,
                    longitude=float(row['longitude']) if row['longitude'] else None,
                    confidence=float(row['confidence']) if row['confidence'] else None,
                    formatted_address=row['formatted_address'],
                    street_name=row['street_name'],
                    street_number=row['street_number'],
                    city=row['city'],
                    state=row['state'],
                    postal_code=row['postal_code'],
                    country=row['country'],
                    source="nominatim",
                    cached=True
                )
        return None

    async def _save_cache(self, query_hash: str, query_text: str,
                          bias_city: Optional[str], bias_state: Optional[str],
                          bias_country: str, result: GeocodeResult,
                          raw_response: dict):
        """Save geocode result to cache."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO geocode_cache (
                    query_hash, query_text, bias_city, bias_state, bias_country,
                    latitude, longitude, confidence, formatted_address,
                    street_name, street_number, city, state, postal_code, country,
                    raw_response
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                ON CONFLICT (query_hash) DO UPDATE SET
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    confidence = EXCLUDED.confidence,
                    formatted_address = EXCLUDED.formatted_address,
                    expires_at = NOW() + INTERVAL '90 days'
            """, query_hash, query_text, bias_city, bias_state, bias_country,
                result.latitude, result.longitude, result.confidence,
                result.formatted_address, result.street_name, result.street_number,
                result.city, result.state, result.postal_code, result.country,
                raw_response)

    def _parse_nominatim_response(self, data: list) -> GeocodeResult:
        """Parse Nominatim API response into GeocodeResult."""
        if not data:
            return GeocodeResult()

        best = data[0]  # Nominatim returns results sorted by relevance

        # Calculate confidence based on importance score
        importance = float(best.get('importance', 0.5))
        confidence = min(importance, 1.0)

        # Parse address components
        address = best.get('address', {})

        return GeocodeResult(
            latitude=float(best.get('lat', 0)),
            longitude=float(best.get('lon', 0)),
            confidence=confidence,
            formatted_address=best.get('display_name'),
            street_name=address.get('road') or address.get('street'),
            street_number=address.get('house_number'),
            city=address.get('city') or address.get('town') or address.get('village'),
            state=address.get('state'),
            postal_code=address.get('postcode'),
            country=address.get('country'),
            source="nominatim",
            cached=False
        )

    async def geocode(self, request: GeocodeRequest) -> GeocodeResult:
        """
        Geocode a location string.

        Uses cache first, then falls back to Nominatim API with rate limiting.
        """
        cache_key = self._make_cache_key(
            request.query, request.bias_city,
            request.bias_state, request.bias_country
        )

        # Check cache first
        cached = await self._check_cache(cache_key)
        if cached:
            logger.debug(f"Cache hit for: {request.query}")
            return cached

        # Rate limit before API call
        await self.rate_limiter.acquire()

        # Build query with bias
        query_parts = [request.query]
        if request.bias_city:
            query_parts.append(request.bias_city)
        if request.bias_state:
            query_parts.append(request.bias_state)
        query_parts.append(request.bias_country)

        full_query = ", ".join(query_parts)

        # Make API request
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/search",
                    params={
                        "q": full_query,
                        "format": "json",
                        "addressdetails": 1,
                        "limit": 1,
                        "countrycodes": "us"  # Limit to US for police scanner data
                    },
                    headers={
                        "User-Agent": self.user_agent
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                result = self._parse_nominatim_response(data)

                # Cache the result (even if empty, to avoid repeated lookups)
                if result.latitude is not None:
                    await self._save_cache(
                        cache_key, request.query,
                        request.bias_city, request.bias_state, request.bias_country,
                        result, data[0] if data else {}
                    )

                logger.info(f"Geocoded '{request.query}' -> ({result.latitude}, {result.longitude})")
                return result

        except httpx.HTTPError as e:
            logger.error(f"Nominatim API error for '{request.query}': {e}")
            return GeocodeResult()
        except Exception as e:
            logger.error(f"Geocoding error for '{request.query}': {e}")
            return GeocodeResult()
