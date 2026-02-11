#!/usr/bin/env python3
import os
import sys
import yaml
import subprocess
import whisper
import logging
import re
import datetime
import pytz  # pip install pytz
from env_config import load_config as _load_config

# === establish absolute paths ===
SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH    = os.path.join(SCRIPT_DIR, "config.yaml")
PARSE_SCRIPT   = os.path.join(SCRIPT_DIR, "parse_and_alert.py")

# Load configuration (env vars take precedence over config.yaml)
cfg = _load_config()

# Logging configuration
log_cfg     = cfg.get("logging", {})
LOG_FILE    = os.path.join(SCRIPT_DIR, log_cfg.get("logfile", "scanner.log"))
LOG_LEVEL   = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
LOG_CONSOLE = log_cfg.get("console", False)

# Ensure log directory exists
log_dir = os.path.dirname(LOG_FILE)
if log_dir:
    os.makedirs(log_dir, exist_ok=True)

# Configure logging
handlers = [logging.FileHandler(LOG_FILE)]
if LOG_CONSOLE:
    handlers.append(logging.StreamHandler())
logging.basicConfig(
    level=LOG_LEVEL,
    handlers=handlers,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Data configuration
d_cfg           = cfg.get("data", {})
TRANSCRIPT_DIR  = os.path.join(SCRIPT_DIR, d_cfg.get("transcript_dir", "data/transcripts"))
DELETE_AUDIO    = d_cfg.get("delete_audio_after_transcribe", True)

# Whisper configuration
wh_cfg     = cfg.get("whisper", {})
MODEL_NAME = wh_cfg.get("model", "base")
DEVICE     = wh_cfg.get("device", "cpu")

# Ensure transcript directory exists
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

# Validate arguments
if len(sys.argv) != 2:
    logging.error("Usage: python3 transcribe_audio.py <audio_file>")
    sys.exit(1)

audio_path = sys.argv[1]
base = os.path.splitext(os.path.basename(audio_path))[0]

# --- Date-parsing logic for filename ---
parts = base.split('-')
transcript_filename = f"{base}.txt"  # fallback

# Look for the epoch segment (must be a 10-digit int, third in filename)
if len(parts) >= 4 and re.match(r'^\d{10}$', parts[2]):
    epoch = int(parts[2])
    # Convert to America/Chicago (Central Time, handles DST)
    dt = datetime.datetime.fromtimestamp(epoch, tz=pytz.UTC).astimezone(pytz.timezone("America/Chicago"))
    date_str = dt.strftime("%Y_%m_%d_%H_%M_%S")
    # Suffix: everything except the epoch, dashed (ID1-ID2-ID4 etc)
    suffix = '-'.join(parts[:2] + parts[3:])
    transcript_filename = f"{date_str}-{suffix}.txt"

transcript_path = os.path.join(TRANSCRIPT_DIR, transcript_filename)

logging.info(f"Starting transcription of {audio_path}")

# Load model and transcribe
model = whisper.load_model(MODEL_NAME, device=DEVICE)
# force fp16=False on CPU
result = model.transcribe(audio_path, fp16=(DEVICE != "cpu"))
text = result.get("text", "").strip()

# If debug logging is enabled, log the full transcript
if logging.getLogger().isEnabledFor(logging.DEBUG):
    logging.debug(f"Full transcript for {audio_path}: {text}")

# Log if transcript is empty
if not text:
    logging.info(f"Transcript for {audio_path} is empty (0 words)")

# Write transcript
with open(transcript_path, "w") as tf:
    tf.write(text)
logging.info(f"Transcribed {audio_path} -> {transcript_path}")

# Optionally delete audio
if DELETE_AUDIO:
    try:
        os.remove(audio_path)
        logging.info(f"Deleted audio file {audio_path}")
    except Exception as e:
        logging.error(f"Failed to delete audio file {audio_path}: {e}")

# Chain to parse_and_alert.py if present
if os.path.exists(PARSE_SCRIPT):
    try:
        subprocess.run(
            [sys.executable, PARSE_SCRIPT, transcript_path],
            check=True
        )
        logging.info(f"Chained parse_and_alert for {transcript_path}")
    except subprocess.CalledProcessError as e:
        logging.error(f"parse_and_alert failed: {e}")

