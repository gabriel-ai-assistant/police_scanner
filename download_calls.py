#!/usr/bin/env python3
import os
import sys
import yaml
import requests
import subprocess
import logging
import fcntl

# === establish absolute paths ===
SCRIPT_DIR        = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH       = os.path.join(SCRIPT_DIR, "config.yaml")
TRANSCRIBE_SCRIPT = os.path.join(SCRIPT_DIR, "transcribe_audio.py")
LOCK_PATH         = os.path.join(SCRIPT_DIR, "download_calls.lock")

# Acquire an exclusive non-blocking lock; exit if already locked
lock_file = open(LOCK_PATH, "w")
try:
    fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    # another instance is running
    sys.exit(0)

# Load configuration
with open(CONFIG_PATH) as f:
    cfg = yaml.safe_load(f)

# Broadcastify configuration
b_cfg         = cfg["broadcastify"]
API_URL       = b_cfg["url"]
PLAYLIST_UUID = b_cfg["playlist_uuid"]
SESSION_KEY   = b_cfg["sessionKey"]
HEADERS       = b_cfg["headers"]
COOKIES       = b_cfg["cookies"]

# Data configuration (make these absolute)
d_cfg     = cfg["data"]
AUDIO_DIR = os.path.join(SCRIPT_DIR, d_cfg["audio_dir"])
SEEN_FILE = os.path.join(SCRIPT_DIR, d_cfg["seen_calls_file"])

# Logging configuration (absolute logfile path)
log_cfg     = cfg.get("logging", {})
LOG_FILE    = os.path.join(SCRIPT_DIR, log_cfg.get("logfile", "scanner.log"))
LOG_LEVEL   = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
LOG_CONSOLE = log_cfg.get("console", False)

# Ensure log directory exists
log_dir = os.path.dirname(LOG_FILE)
if log_dir:
    os.makedirs(log_dir, exist_ok=True)

# Configure logging handlers
handlers = [logging.FileHandler(LOG_FILE)]
if LOG_CONSOLE:
    handlers.append(logging.StreamHandler())
logging.basicConfig(
    level=LOG_LEVEL,
    handlers=handlers,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logging.info(f"Starting download_calls.py run (last_pos={b_cfg.get('last_pos', 0)})")

# Ensure directories exist
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)

# Load list of already-downloaded call IDs
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE) as f:
        seen = set(f.read().splitlines())
    logging.debug(f"Loaded {len(seen)} seen call IDs")
else:
    seen = set()
    logging.debug("No seen calls file found, starting fresh")

# Poll the Calls API
payload = {
    "pos":           b_cfg.get("last_pos", 0),
    "doInit":        0,
    "systemId":      0,
    "sid":           0,
    "playlist_uuid": PLAYLIST_UUID,
    "sessionKey":    SESSION_KEY
}
try:
    resp = requests.post(API_URL, headers=HEADERS, cookies=COOKIES, data=payload)
    resp.raise_for_status()
    data = resp.json()
    logging.info(
        f"Fetched live-calls payload: {len(data.get('calls', []))} calls "
        f"(serverTime={data.get('serverTime')}, lastPos={data.get('lastPos')})"
    )
except Exception as e:
    logging.error(f"Failed to poll Calls API: {e}")
    sys.exit(1)

# Download any new calls
for call in data.get("calls", []):
    # unique ID per call+filename
    cid = f"{call.get('id')}-{call.get('filename')}"
    if not (call.get("id") and call.get("filename")):
        logging.warning(f"Skipping malformed call entry: {call}")
        continue
    if cid in seen:
        continue

    h  = call.get("hash")
    fn = call.get("filename")
    if not h:
        logging.warning(f"Skipping call {cid} without hash")
        continue

    url = f"https://calls.broadcastify.com/{h}/2000/{fn}.m4a"
    out = os.path.join(AUDIO_DIR, f"{cid}.m4a")
    logging.info(f"Downloading call {cid} from {url}")

    try:
        dl = requests.get(url, headers=HEADERS, cookies=COOKIES, timeout=30)
        dl.raise_for_status()
        with open(out, "wb") as f:
            f.write(dl.content)
        logging.info(f"Successfully downloaded {out}")

        # Chain to transcription using absolute paths
        subprocess.run(
            [sys.executable, TRANSCRIBE_SCRIPT, out],
            check=True
        )
        logging.info(f"Chained transcription for {cid}")

    except Exception as e:
        logging.error(f"Download or chain failed for {cid}: {e}")

    seen.add(cid)

# Save updated seen list
with open(SEEN_FILE, "w") as f:
    f.write("\n".join(seen))
logging.debug(f"Saved {len(seen)} seen call IDs to {SEEN_FILE}")

# Update last_pos in config and save
if "lastPos" in data:
    b_cfg["last_pos"] = data["lastPos"]
    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(cfg, f)
    logging.info(f"Updated last_pos to {data['lastPos']} in {CONFIG_PATH}")

logging.info("Completed download_calls.py run")

