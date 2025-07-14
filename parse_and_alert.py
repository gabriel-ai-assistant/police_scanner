#!/usr/bin/env python3
import os
import sys
import yaml
import subprocess
import logging
import re

# Determine base directory and config path
SCRIPT_DIR   = os.path.dirname(os.path.realpath(__file__))
CONFIG_PATH  = os.path.join(SCRIPT_DIR, "config.yaml")

# Load configuration
def load_config():
    if not os.path.exists(CONFIG_PATH):
        logging.error(f"Config file not found: {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)

cfg = load_config()

# Logging configuration
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

logging.info("Starting parse_and_alert.py run")

# Keywords configuration
kw_cfg         = cfg.get("keywords", {})
KEYWORDS_FILE  = kw_cfg.get("file")
CASE_SENSITIVE = kw_cfg.get("case_sensitive", False)
MIN_HITS       = kw_cfg.get("min_hits", 1)

# Signal configuration
sig_cfg      = cfg.get("signal", {})
SIG_CLI_BIN  = sig_cfg.get("signal_cli_bin")
FROM_NUMBER  = sig_cfg.get("from_number")
RECIPIENTS   = sig_cfg.get("recipients", [])
MSG_TEMPLATE = sig_cfg.get("message_template", "{transcript}")

# Resolve keywords file path
keywords_path = KEYWORDS_FILE if os.path.isabs(KEYWORDS_FILE) else os.path.join(SCRIPT_DIR, KEYWORDS_FILE)
if not os.path.exists(keywords_path):
    logging.error(f"Keywords file not found: {keywords_path}")
    sys.exit(1)

# Load and normalize keywords
with open(keywords_path) as f:
    raw_kws = [line.strip() for line in f if line.strip()]
keywords = raw_kws if CASE_SENSITIVE else [kw.lower() for kw in raw_kws]
logging.debug(f"Loaded {len(keywords)} keywords (case_sensitive={CASE_SENSITIVE})")

# Compile keyword patterns for word-boundary matching
patterns = []
flags = 0 if CASE_SENSITIVE else re.IGNORECASE
for kw in keywords:
    # if it's a simple word (alnum/apostrophe), anchor with \b
    if re.fullmatch(r"[\w']+", kw):
        pat = re.compile(rf"\b{re.escape(kw)}\b", flags)
    else:
        # otherwise just a substring match
        pat = re.compile(re.escape(kw), flags)
    patterns.append((kw, pat))

# Validate arguments
if len(sys.argv) != 2:
    logging.error("Usage: python3 parse_and_alert.py <transcript_file>")
    sys.exit(1)

transcript_path = sys.argv[1]
# resolve to absolute
if not os.path.isabs(transcript_path):
    transcript_path = os.path.join(SCRIPT_DIR, transcript_path)
if not os.path.exists(transcript_path):
    logging.error(f"Transcript not found: {transcript_path}")
    sys.exit(1)

# Read transcript
with open(transcript_path) as f:
    transcript = f.read()
search_text = transcript if CASE_SENSITIVE else transcript.lower()

# Find matching keywords
matches = [kw for kw, pat in patterns if pat.search(search_text)]
count = len(matches)
logging.info(f"Found {count} keyword hit(s) in {transcript_path}")

if count >= MIN_HITS:
    unique_hits = sorted(set(matches))
    logging.info(f"Matched keywords: {unique_hits}")
    call_id = os.path.splitext(os.path.basename(transcript_path))[0]
    msg = MSG_TEMPLATE.format(
        keywords=", ".join(unique_hits),
        call_id=call_id,
        transcript=transcript
    )
    # send alerts
    for recipient in RECIPIENTS:
        try:
            subprocess.run([
                SIG_CLI_BIN,
                "-u", FROM_NUMBER,
                "send", recipient,
                "-m", msg
            ], check=True)
            logging.info(f"Alert sent to {recipient} for call {call_id}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Signal send failed for {recipient}: {e}")
else:
    logging.info(f"No keyword hits (found {count}, min_hits={MIN_HITS}) in {transcript_path}")

logging.info("Completed parse_and_alert.py run")

