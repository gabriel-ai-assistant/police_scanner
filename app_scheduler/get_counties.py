import os
import json
import time
import hmac
import base64
import logging
import psycopg2
import requests
from hashlib import sha256
from dotenv import load_dotenv

load_dotenv()

DEFAULT_BASE_URL = os.getenv("BCFY_BASE_URL", "https://api.bcfy.io").rstrip("/")
COUNTIES_PATH_TEMPLATE = "/common/v1/counties/{}"  # path param: stid
COUNTY_DETAIL_PATH_TEMPLATE = "/common/v1/county/{}"  # path param: ctid


# =========================================================
# Logging setup
# =========================================================
def setup_logging(verbose: bool):
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )


# =========================================================
# JWT token builder
# =========================================================
def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def build_jwt(api_key: str, api_key_id: str, app_id: str, ttl: int = 3600) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT", "kid": api_key_id}
    payload = {"iss": app_id, "iat": now, "exp": now + ttl}
    header_b64 = b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(api_key.encode(), f"{header_b64}.{payload_b64}".encode(), sha256).digest()
    return f"{header_b64}.{payload_b64}.{b64url(sig)}"


# =========================================================
# DB connection
# =========================================================
def get_conn():
    return psycopg2.connect(
        host=os.getenv("PGHOST"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        dbname=os.getenv("PGDATABASE"),
        port=int(os.getenv("PGPORT", "5432")),
    )


# =========================================================
# HTTP helper (with persistent session + retries)
# =========================================================
def fetch_json(url: str, headers: dict, retries: int = 3, timeout: int = 15):
    if not hasattr(fetch_json, "session"):
        fetch_json.session = requests.Session()

    for attempt in range(1, retries + 1):
        try:
            resp = fetch_json.session.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logging.warning(f"Attempt {attempt}/{retries} failed for {url}: {e}")
            time.sleep(min(2**attempt, 10))
    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts")


# =========================================================
# Upsert / update helpers
# =========================================================
def upsert_county(conn, county: dict):
    """Insert or update a county row in Postgres."""
    sql = """
    INSERT INTO bcfy_counties (
        cntid, stid, coid,
        county_name, county_header, type, lat, lon, range,
        fips, timezone_str, state_name, state_code,
        country_name, country_code, is_active, sync, fetched_at, raw_json
    )
    VALUES (
        %(cntid)s, %(stid)s, %(coid)s,
        %(county_name)s, %(county_header)s, %(type)s, %(lat)s, %(lon)s, %(range)s,
        %(fips)s, %(timezone_str)s, %(state_name)s, %(state_code)s,
        %(country_name)s, %(country_code)s, %(is_active)s, %(sync)s, NOW(), %(raw_json)s::jsonb
    )
    ON CONFLICT (cntid) DO UPDATE
      SET county_name   = EXCLUDED.county_name,
          county_header = EXCLUDED.county_header,
          type          = EXCLUDED.type,
          lat           = EXCLUDED.lat,
          lon           = EXCLUDED.lon,
          range         = EXCLUDED.range,
          fips          = EXCLUDED.fips,
          timezone_str  = EXCLUDED.timezone_str,
          state_name    = EXCLUDED.state_name,
          state_code    = EXCLUDED.state_code,
          country_name  = EXCLUDED.country_name,
          country_code  = EXCLUDED.country_code,
          is_active     = EXCLUDED.is_active,
          sync          = EXCLUDED.sync,
          raw_json      = EXCLUDED.raw_json,
          fetched_at    = NOW();
    """
    cur = conn.cursor()
    cur.execute(sql, county)
    conn.commit()
    cur.close()


# =========================================================
# Main logic
# =========================================================
def main(verbose=False):
    setup_logging(verbose)
    log = logging.getLogger("get_counties")

    api_key = os.getenv("BCFY_API_KEY")
    api_key_id = os.getenv("BCFY_API_KEY_ID")
    app_id = os.getenv("BCFY_APP_ID")
    base_url = os.getenv("BCFY_BASE_URL", DEFAULT_BASE_URL)

    jwt = build_jwt(api_key, api_key_id, app_id)
    headers = {"Authorization": f"Bearer {jwt}"}

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT s.stid, s.state_name, s.coid, c.country_name
        FROM bcfy_states s
        JOIN bcfy_countries c ON s.coid = c.coid
        WHERE s.sync = TRUE;
    """)
    states = cur.fetchall()
    if not states:
        log.warning("No states found with sync=true.")
        return

    log.info(f"Found {len(states)} states to sync counties for.")
    total_inserted, total_skipped = 0, 0

    for idx, (stid, state_name, coid, country_name) in enumerate(states, start=1):
        url = f"{base_url}{COUNTIES_PATH_TEMPLATE.format(stid)}"
        log.info(f"[{idx}/{len(states)}] Fetching counties list for {state_name}, {country_name} (stid={stid})")

        try:
            data = fetch_json(url, headers)
        except Exception as e:
            log.error(f"Failed to fetch counties for {state_name} ({stid}): {e}")
            continue

        counties = []
        if isinstance(data, dict):
            counties = data.get("counties") or data.get("data") or []
        elif isinstance(data, list):
            counties = data

        if not counties:
            log.info(f"No counties returned for {state_name}")
            continue

        log.info(f"Retrieved {len(counties)} counties for {state_name}")

        # PERF FIX: Batch county detail fetching instead of N+1 individual requests.
        # First, collect all county IDs, then fetch details in batches.
        county_ids = []
        county_map = {}
        for c in counties:
            ctid = c.get("ctid") or c.get("cntid") or c.get("id")
            if not ctid:
                total_skipped += 1
                log.warning(f"Skipping county (missing ctid): {c}")
                continue
            county_ids.append(ctid)
            county_map[ctid] = c

        # Fetch details in batches (the external API only supports single-county
        # detail endpoints, so we still make individual calls but with concurrency
        # via a thread pool to avoid serial blocking).
        import concurrent.futures

        def fetch_county_detail(ctid):
            detail_url = f"{base_url}{COUNTY_DETAIL_PATH_TEMPLATE.format(ctid)}"
            try:
                return ctid, fetch_json(detail_url, headers)
            except Exception as e:
                log.warning(f"Failed to fetch detail for county {ctid}: {e}")
                return ctid, None

        BATCH_SIZE = 10  # concurrent requests per batch
        details = {}
        for i in range(0, len(county_ids), BATCH_SIZE):
            batch = county_ids[i:i + BATCH_SIZE]
            with concurrent.futures.ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
                results = executor.map(fetch_county_detail, batch)
                for ctid, detail in results:
                    if detail is not None:
                        details[ctid] = detail
            time.sleep(0.2)  # small delay between batches

        for ctid in county_ids:
            if ctid not in details:
                total_skipped += 1
                continue
            detail = details[ctid]
            c = county_map[ctid]
            c.update(detail)

            row = {
                "cntid": int(ctid),
                "stid": int(detail.get("stid", stid)),
                "coid": int(detail.get("coid", coid)),
                "county_name": detail.get("county_name"),
                "county_header": detail.get("county_header"),
                "type": int(detail.get("type")) if detail.get("type") not in (None, "") else None,
                "lat": float(detail.get("lat")) if detail.get("lat") not in (None, "") else None,
                "lon": float(detail.get("lon")) if detail.get("lon") not in (None, "") else None,
                "range": int(detail.get("range")) if detail.get("range") not in (None, "") else None,
                "fips": detail.get("fips"),
                "timezone_str": detail.get("timezone") or detail.get("timezone_str"),
                "state_name": detail.get("state_name") or state_name,
                "state_code": detail.get("state_code"),
                "country_name": detail.get("country_name") or country_name,
                "country_code": detail.get("country_code"),
                "is_active": c.get("is_active", True),
                "sync": c.get("sync", False),
                "raw_json": json.dumps(detail, separators=(",", ":")),
            }

            try:
                upsert_county(conn, row)
                total_inserted += 1
            except Exception as e:
                total_skipped += 1
                log.warning(f"Failed to upsert county {ctid}: {e}")

        log.info(f"Completed {state_name}: {total_inserted} inserted/updated, {total_skipped} skipped so far.")

    conn.close()
    log.info(f"All done. Inserted/updated: {total_inserted}, skipped: {total_skipped}.")


# =========================================================
# Entrypoint
# =========================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sync counties with full detail for all states where sync=true.")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    main(verbose=args.verbose)
