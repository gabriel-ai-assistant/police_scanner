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

load_dotenv()

DEFAULT_BASE_URL = os.getenv("BCFY_BASE_URL", "https://api.bcfy.io").rstrip("/")
STATES_PATH_TEMPLATE = "/common/v1/states/{}"   # <-- Path parameter

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
# JWT builder
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
# HTTP helper
# =========================================================
def fetch_json(url: str, headers: dict, retries: int = 3, timeout: int = 15):
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logging.warning(f"Attempt {attempt}/{retries} failed for {url}: {e}")
            time.sleep(min(2**attempt, 10))
    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts")


# =========================================================
# Upsert states
# =========================================================
def upsert_states(conn, coid: int, states: list):
    sql = """
    INSERT INTO bcfy_states (stid, state_name, state_code, coid, raw_json)
    VALUES (%s, %s, %s, %s, %s::jsonb)
    ON CONFLICT (stid) DO UPDATE
      SET state_name = EXCLUDED.state_name,
          state_code = EXCLUDED.state_code,
          coid       = EXCLUDED.coid,
          raw_json   = EXCLUDED.raw_json;
    """
    cur = conn.cursor()
    for s in states:
        stid = s.get("stid") or s.get("id")
        name = s.get("state_name") or s.get("name")
        code = s.get("state_code") or s.get("code")
        cur.execute(sql, (stid, name, code, coid, json.dumps(s)))
    conn.commit()
    cur.close()


# =========================================================
# Main process
# =========================================================
def main(verbose=False):
    setup_logging(verbose)
    log = logging.getLogger("get_states")

    api_key = os.getenv("BCFY_API_KEY")
    api_key_id = os.getenv("BCFY_API_KEY_ID")
    app_id = os.getenv("BCFY_APP_ID")
    base_url = os.getenv("BCFY_BASE_URL", DEFAULT_BASE_URL)

    jwt = build_jwt(api_key, api_key_id, app_id)
    headers = {"Authorization": f"Bearer {jwt}"}

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT coid, country_name FROM bcfy_countries WHERE sync = TRUE;")
    countries = cur.fetchall()

    if not countries:
        log.warning("No countries with sync=true found.")
        return

    log.info(f"Found {len(countries)} countries to sync states for.")

    for coid, name in countries:
        url = f"{base_url}{STATES_PATH_TEMPLATE.format(coid)}"
        log.info(f"Fetching states for {name} (coid={coid}) → {url}")

        try:
            data = fetch_json(url, headers)
        except Exception as e:
            log.error(f"Failed to fetch states for {name} (coid={coid}): {e}")
            continue

        if isinstance(data, dict):
            states = data.get("states") or data.get("data") or []
        elif isinstance(data, list):
            states = data
        else:
            log.warning(f"Unexpected response for {name}: {type(data)}")
            continue

        if not states:
            log.info(f"No states returned for {name}")
            continue

        upsert_states(conn, coid, states)
        log.info(f"Inserted/updated {len(states)} states for {name}")

    conn.close()
    log.info("All done.")


# =========================================================
# Entrypoint
# =========================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sync states for all countries with sync=true.")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    main(verbose=args.verbose)
