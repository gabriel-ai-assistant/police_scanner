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

# =========================================================
# Load environment
# =========================================================
load_dotenv()

DEFAULT_BASE_URL = os.getenv("BCFY_BASE_URL", "https://api.bcfy.io").rstrip("/")
PLAYLISTS_PATH = "/calls/v1/playlists_public"
PLAYLIST_DETAIL_PATH = "/calls/v1/playlist_get/?uuid={}"


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
    token = f"{header_b64}.{payload_b64}.{b64url(sig)}"
    return token


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
# HTTP helper with persistent session
# =========================================================
def fetch_json(url: str, headers: dict, retries: int = 3, timeout: int = 15):
    if not hasattr(fetch_json, "session"):
        fetch_json.session = requests.Session()

    for attempt in range(1, retries + 1):
        try:
            resp = fetch_json.session.get(url, headers=headers, timeout=timeout)
            logging.debug(f"HTTP {resp.status_code} {url}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logging.warning(f"Attempt {attempt}/{retries} failed for {url}: {e}")
            time.sleep(min(2**attempt, 10))
    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts")


# =========================================================
# Upsert playlists
# =========================================================
def upsert_playlist(conn, p: dict):
    sql = """
    INSERT INTO bcfy_playlists (
        uuid, name, descr, ts, last_seen, listeners, public,
        max_groups, num_groups, ctids, groups_json, fetched_at, raw_json
    )
    VALUES (
        %(uuid)s, %(name)s, %(descr)s, %(ts)s, %(last_seen)s, %(listeners)s, %(public)s,
        %(max_groups)s, %(num_groups)s, %(ctids)s::jsonb, %(groups_json)s::jsonb, NOW(), %(raw_json)s::jsonb
    )
    ON CONFLICT (uuid) DO UPDATE
      SET name        = EXCLUDED.name,
          descr       = EXCLUDED.descr,
          ts          = EXCLUDED.ts,
          last_seen   = EXCLUDED.last_seen,
          listeners   = EXCLUDED.listeners,
          public      = EXCLUDED.public,
          max_groups  = EXCLUDED.max_groups,
          num_groups  = EXCLUDED.num_groups,
          ctids       = EXCLUDED.ctids,
          groups_json = EXCLUDED.groups_json,
          raw_json    = EXCLUDED.raw_json,
          fetched_at  = NOW();
    """
    cur = conn.cursor()
    cur.execute(sql, p)
    conn.commit()
    cur.close()


# =========================================================
# Main
# =========================================================
def main(verbose=False):
    setup_logging(verbose)
    log = logging.getLogger("get_playlists")

    api_key = os.getenv("BCFY_API_KEY")
    api_key_id = os.getenv("BCFY_API_KEY_ID")
    app_id = os.getenv("BCFY_APP_ID")
    base_url = os.getenv("BCFY_BASE_URL", DEFAULT_BASE_URL)

    if not api_key or not api_key_id or not app_id:
        log.error("Missing API credentials. Check your .env file.")
        return

    jwt = build_jwt(api_key, api_key_id, app_id)
    headers = {"Authorization": f"Bearer {jwt}"}

    log.info("JWT built successfully.")
    log.debug(f"JWT (truncated): {jwt[:50]}...")

    # =========================================================
    # Fetch all public playlists
    # =========================================================
    playlists_url = f"{base_url}{PLAYLISTS_PATH}"
    log.info(f"Fetching all public playlists from {playlists_url}")

    try:
        playlists = fetch_json(playlists_url, headers)
    except Exception as e:
        log.error(f"Failed to fetch playlist list: {e}")
        return

    if not playlists:
        log.warning("No public playlists returned.")
        return

    log.info(f"Found {len(playlists)} public playlists.")

    conn = get_conn()
    inserted, skipped = 0, 0

    for idx, summary in enumerate(playlists, start=1):
        uuid = summary.get("uuid")
        name = summary.get("name", "Unknown")

        if not uuid:
            log.warning(f"Skipping playlist with missing UUID: {summary}")
            skipped += 1
            continue

        detail_url = f"{base_url}{PLAYLIST_DETAIL_PATH.format(uuid)}"
        log.info(f"[{idx}/{len(playlists)}] Fetching details for {name} ({uuid})")

        try:
            detail = fetch_json(detail_url, headers)
        except Exception as e:
            log.warning(f"Failed to fetch playlist detail for {uuid}: {e}")
            skipped += 1
            continue

        row = {
            "uuid": uuid,
            "name": detail.get("name") or summary.get("name"),
            "descr": detail.get("descr") or summary.get("descr"),
            "ts": int(detail.get("ts")) if detail.get("ts") else None,
            "last_seen": int(detail.get("last_seen")) if detail.get("last_seen") else None,
            "listeners": int(detail.get("listeners")) if detail.get("listeners") else None,
            "public": str(detail.get("public")).lower() in ("1", "true", "yes"),
            "max_groups": detail.get("maxGroups"),
            "num_groups": detail.get("numGroups"),
            "ctids": json.dumps(detail.get("ctids") or summary.get("counties") or []),
            "groups_json": json.dumps(detail.get("groups") or []),
            "raw_json": json.dumps(detail, separators=(",", ":")),
        }

        try:
            upsert_playlist(conn, row)
            inserted += 1
            if inserted % 10 == 0:
                log.info(f"Progress: inserted/updated {inserted} playlists...")
        except Exception as e:
            skipped += 1
            log.warning(f"Failed to upsert playlist {uuid}: {e}")

    conn.close()
    log.info(f"All done. Inserted/updated: {inserted}, skipped: {skipped}.")


# =========================================================
# Entrypoint
# =========================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sync all public Broadcastify playlists with details.")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    main(verbose=args.verbose)
