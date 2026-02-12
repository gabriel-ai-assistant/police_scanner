import argparse
import base64
import hmac
import json
import logging
import os
import time
from hashlib import sha256

import psycopg2
import requests
from dotenv import load_dotenv

# =========================================================
# CONFIGURATION
# =========================================================
load_dotenv()  # Load .env file automatically

DEFAULT_BASE_URL = os.getenv("BCFY_BASE_URL", "https://api.bcfy.io").rstrip("/")
COUNTRIES_PATH = "/common/v1/countries"

# =========================================================
# LOGGING SETUP
# =========================================================
def setup_logging(verbose: bool):
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )

# =========================================================
# JWT TOKEN BUILDER
# =========================================================
def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def build_jwt(api_key: str, api_key_id: str, app_id: str, ttl: int = 3600) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT", "kid": api_key_id}
    payload = {"iss": app_id, "iat": now, "exp": now + ttl}

    header_b64 = b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = b64url(json.dumps(payload, separators=(",", ":")).encode())

    msg = f"{header_b64}.{payload_b64}".encode()
    sig = hmac.new(api_key.encode(), msg, sha256).digest()
    return f"{header_b64}.{payload_b64}.{b64url(sig)}"

# =========================================================
# DATABASE CONNECTION
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
# MAIN FUNCTION
# =========================================================
def main():
    parser = argparse.ArgumentParser(description="Pull Broadcastify countries and store in Postgres")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    setup_logging(args.verbose)

    log = logging.getLogger("get_countries")

    # Load env
    api_key = os.getenv("BCFY_API_KEY")
    api_key_id = os.getenv("BCFY_API_KEY_ID")
    app_id = os.getenv("BCFY_APP_ID")
    base_url = os.getenv("BCFY_BASE_URL", DEFAULT_BASE_URL)

    missing = [k for k, v in {
        "BCFY_API_KEY": api_key,
        "BCFY_API_KEY_ID": api_key_id,
        "BCFY_APP_ID": app_id
    }.items() if not v]
    if missing:
        log.error(f"Missing required environment variables: {', '.join(missing)}")
        return

    # Build JWT
    jwt = build_jwt(api_key, api_key_id, app_id)
    log.info("JWT built successfully.")

    url = f"{base_url}{COUNTRIES_PATH}"
    headers = {"Authorization": f"Bearer {jwt}"}
    log.info(f"Fetching {url}")

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.error(f"API request failed: {e}")
        return

    if isinstance(data, dict):
        countries = data.get("countries") or data.get("data") or []
    elif isinstance(data, list):
        countries = data
    else:
        log.error(f"Unexpected API format: {type(data)}")
        return

    log.info(f"Fetched {len(countries)} records.")

    # Write to Postgres
    try:
        conn = get_conn()
        cur = conn.cursor()
    except Exception as e:
        log.error(f"Postgres connection failed: {e}")
        return

    sql = """
    INSERT INTO bcfy_countries (coid, country_name, country_code, iso_alpha2, raw_json)
    VALUES (%s, %s, %s, %s, %s::jsonb)
    ON CONFLICT (coid) DO UPDATE
      SET country_name = EXCLUDED.country_name,
          country_code = EXCLUDED.country_code,
          iso_alpha2 = EXCLUDED.iso_alpha2,
          raw_json = EXCLUDED.raw_json;
    """

    for c in countries:
        try:
            coid = c.get("coid") or c.get("id")
            name = c.get("country_name") or c.get("name")
            code = c.get("country_code") or c.get("code")
            iso = c.get("iso_alpha2") or c.get("isoAlpha2")
            cur.execute(sql, (coid, name, code, iso, json.dumps(c)))
        except Exception as e:
            log.warning(f"Failed to insert record {c}: {e}")

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM bcfy_countries;")
    count = cur.fetchone()[0]
    log.info(f"Database now has {count} records in bcfy_countries.")
    cur.close()
    conn.close()
    log.info("Done.")

if __name__ == "__main__":
    main()
