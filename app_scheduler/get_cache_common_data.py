import os
import time
import json
import hmac
import base64
import hashlib
import logging
import requests
import psycopg2.extras
from db import get_conn


# ============================================================
# Configure logging – always show on console
# ============================================================
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)


# ============================================================
# JWT Builder with detailed diagnostics
# ============================================================
def build_jwt():
    logging.info("🔑 Building Broadcastify JWT token...")
    api_key = os.getenv("BCFY_API_KEY")
    api_key_id = os.getenv("BCFY_API_KEY_ID")
    app_id = os.getenv("BCFY_APP_ID")

    logging.debug(f"API_KEY_ID={api_key_id}, APP_ID={app_id}, API_KEY length={len(api_key) if api_key else 0}")

    if not all([api_key, api_key_id, app_id]):
        raise RuntimeError("❌ Missing required Broadcastify API credentials")

    header = {"alg": "HS256", "typ": "JWT", "kid": api_key_id}
    iat = int(time.time())
    exp = iat + 3600
    payload = {"iss": app_id, "iat": iat, "exp": exp}

    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode().rstrip("=")

    header_b64 = b64url(json.dumps(header).encode())
    payload_b64 = b64url(json.dumps(payload).encode())
    token_data = f"{header_b64}.{payload_b64}"

    logging.debug(f"Header B64: {header_b64}")
    logging.debug(f"Payload B64: {payload_b64}")

    signature = hmac.new(api_key.encode(), token_data.encode(), hashlib.sha256).digest()
    signature_b64 = b64url(signature)
    jwt_token = f"{token_data}.{signature_b64}"

    logging.info(f"✅ JWT built successfully (first 60 chars): {jwt_token[:60]}...")
    return jwt_token


# ============================================================
# Fetch function with HTTP diagnostics
# ============================================================
def fetch_json(endpoint: str, headers: dict):
    url = f"{os.getenv('BCFY_BASE_URL', 'https://api.bcfy.io')}{endpoint}"
    logging.info(f"🌎 Fetching: {url}")
    try:
        r = requests.get(url, headers=headers, timeout=15)
        logging.debug(f"Response status: {r.status_code}")
        if r.status_code != 200:
            logging.error(f"❌ Non-200 response from {endpoint}: {r.text}")
        return r.json()
    except Exception as e:
        logging.exception(f"💥 Request to {endpoint} failed: {e}")
        return {}


# ============================================================
# Refresh Common Data
# ============================================================
def refresh_common():
    logging.info("🚀 Starting refresh_common()...")

    jwt_token = build_jwt()
    headers = {"Authorization": f"Bearer {jwt_token}"}

    logging.info("📡 Requesting /common/countries ...")
    countries = fetch_json("/common/countries", headers)
    logging.info(f"Countries raw keys: {list(countries.keys()) if countries else 'None'}")

    logging.info("📡 Requesting /common/states ...")
    states = fetch_json("/common/states", headers)
    logging.info(f"States raw keys: {list(states.keys()) if states else 'None'}")

    try:
        with get_conn() as conn:
            logging.info("💾 Connected to database successfully.")
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                logging.info("📝 Inserting/Updating countries...")
                for c in countries.get("countries", []):
                    logging.debug(f"Upserting country: {c}")
                    cur.execute(
                        """
                        INSERT INTO bcfy_countries (coid, country_name, country_code, iso_alpha2, raw_json)
                        VALUES (%s,%s,%s,%s,%s)
                        ON CONFLICT (coid) DO UPDATE SET
                          country_name=EXCLUDED.country_name,
                          country_code=EXCLUDED.country_code,
                          iso_alpha2=EXCLUDED.iso_alpha2,
                          raw_json=EXCLUDED.raw_json,
                          fetched_at=NOW();
                        """,
                        (
                            c["coid"],
                            c["country_name"],
                            c["country_code"],
                            c.get("iso_alpha2"),
                            json.dumps(c),
                        ),
                    )

                logging.info("📝 Inserting/Updating states...")
                for s in states.get("states", []):
                    logging.debug(f"Upserting state: {s}")
                    cur.execute(
                        """
                        INSERT INTO bcfy_states (stid, coid, state_name, state_code, raw_json)
                        VALUES (%s,%s,%s,%s,%s)
                        ON CONFLICT (stid) DO UPDATE SET
                          state_name=EXCLUDED.state_name,
                          state_code=EXCLUDED.state_code,
                          raw_json=EXCLUDED.raw_json,
                          fetched_at=NOW();
                        """,
                        (
                            s["stid"],
                            s["coid"],
                            s["state_name"],
                            s["state_code"],
                            json.dumps(s),
                        ),
                    )

                conn.commit()
                logging.info(
                    f"✅ DB commit complete: {len(countries.get('countries', []))} countries, "
                    f"{len(states.get('states', []))} states."
                )

    except Exception as e:
        logging.exception(f"❌ Database operation failed: {e}")


# ============================================================
# Main entrypoint
# ============================================================
def main():
    logging.info("🟢 get_cache_common_data.py starting main() ...")
    try:
        refresh_common()
    except Exception as e:
        logging.exception(f"💥 refresh_common() crashed: {e}")


if __name__ == "__main__" or __name__ == "jobs.get_cache_common_data":
    main()
