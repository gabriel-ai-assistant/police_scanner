import os, requests, logging, psycopg2.extras
from .db import get_conn

BASE_URL = os.getenv("BCFY_BASE_URL", "https://api.broadcastify.com")
API_KEY  = os.getenv("BCFY_API_KEY")  # put this in your .env later

def refresh_common():
    logging.info("Refreshing Broadcastify common data…")
    try:
        countries = requests.get(f"{BASE_URL}/common/countries", params={"api_key": API_KEY}).json()
        states    = requests.get(f"{BASE_URL}/common/states",    params={"api_key": API_KEY}).json()

        with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            for c in countries.get("countries", []):
                cur.execute("""
                    INSERT INTO bcfy_countries (coid, country_name, country_code, iso_alpha2, raw_json)
                    VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT (coid) DO UPDATE SET
                      country_name=EXCLUDED.country_name,
                      country_code=EXCLUDED.country_code,
                      iso_alpha2=EXCLUDED.iso_alpha2,
                      raw_json=EXCLUDED.raw_json,
                      fetched_at=NOW();
                """, (c["coid"], c["country_name"], c["country_code"], c.get("iso_alpha2"), c))
            for s in states.get("states", []):
                cur.execute("""
                    INSERT INTO bcfy_states (stid, coid, state_name, state_code, raw_json)
                    VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT (stid) DO UPDATE SET
                      state_name=EXCLUDED.state_name,
                      state_code=EXCLUDED.state_code,
                      raw_json=EXCLUDED.raw_json,
                      fetched_at=NOW();
                """, (s["stid"], s["coid"], s["state_name"], s["state_code"], s))
        logging.info("Common cache updated successfully.")
    except Exception as e:
        logging.exception(f"Common cache update failed: {e}")
