# =============================================================================
# DEPRECATED / LEGACY — kept for reference only.
#
# This module uses faster_whisper for local GPU-based transcription.
# The production transcription path is worker.py (Celery + OpenAI Whisper API).
#
# Key differences from worker.py:
#   - Uses faster_whisper (local GPU) instead of OpenAI Whisper API
#   - References column "recording_id" instead of "call_uid"
#   - Contains hardcoded DB credentials (not production-safe)
#
# Do not use in production. Retained in case the local faster_whisper path
# is needed for offline/GPU transcription in the future.
# =============================================================================

import logging
import os
import re
import tempfile
from datetime import UTC, datetime

import boto3
import psycopg2
from botocore.exceptions import ClientError
from faster_whisper import WhisperModel

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

DB = {
    "host": os.getenv("PGHOST", "db"),
    "port": os.getenv("PGPORT", "5432"),
    "dbname": os.getenv("PGDATABASE", "scanner"),
    "user": os.getenv("PGUSER", "scanner"),
    "password": os.getenv("PGPASSWORD"),
}

BUCKET_PATH = os.getenv("AUDIO_BUCKET_PATH", "calls")
model = WhisperModel("medium", device="cuda", compute_type="float16")
s3 = boto3.client("s3")


def _extract_call_uid_from_key(s3_key: str) -> str:
    """Extract call_uid from S3 key (works for both hierarchical and flat paths).

    Hierarchical: calls/playlist_id=.../year=.../call_{call_uid}.wav -> {call_uid}
    Flat: calls/{call_uid}.wav -> {call_uid}
    """
    # Try to extract from hierarchical path (call_{call_uid}.wav)
    match = re.search(r'call_([^/]+)\.wav$', s3_key)
    if match:
        return match.group(1)

    # Flat path: calls/{call_uid}.wav
    basename = os.path.basename(s3_key)
    return os.path.splitext(basename)[0]


def download_audio_with_fallback(bucket: str, s3_key: str, local_path: str) -> str:
    """Download audio file with dual-read fallback for backward compatibility.

    Args:
        bucket: S3 bucket name
        s3_key: Primary S3 object key (hierarchical or flat)
        local_path: Local file path to save downloaded audio

    Returns:
        The s3_key that was successfully used for download
    """
    try:
        # Try primary path first
        s3.download_file(bucket, s3_key, local_path)
        log.debug(f"Downloaded from primary path: {s3_key}")
        return s3_key
    except ClientError as e:
        if e.response['Error']['Code'] == '404' or 'NoSuchKey' in str(e):
            # Try legacy flat path
            call_uid = _extract_call_uid_from_key(s3_key)
            legacy_key = f"{BUCKET_PATH}/{call_uid}.wav"

            if legacy_key != s3_key:  # Avoid infinite loop
                log.info(f"Fallback: trying legacy path {legacy_key}")
                try:
                    s3.download_file(bucket, legacy_key, local_path)
                    log.info(f"Downloaded from legacy path: {legacy_key}")
                    return legacy_key
                except ClientError:
                    pass  # Fall through to re-raise original error

        log.error(f"Failed to download from both {s3_key} and legacy path")
        raise


def get_pending_calls():
    with psycopg2.connect(**DB) as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id, s3_path
            FROM bcfy_calls_raw
            WHERE processed = false
            ORDER BY id
            LIMIT 10;
        """)
        return cur.fetchall()

def mark_processed(cur, call_id, success, error=None):
    cur.execute("""
        UPDATE bcfy_calls_raw
        SET processed=%s, last_attempt=%s, error=%s
        WHERE id=%s;
    """, (success, datetime.now(UTC), error, call_id))

def transcribe_file(_call_id, s3_uri):
    bucket, key = s3_uri.replace("s3://", "").split("/", 1)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        try:
            download_audio_with_fallback(bucket, key, tmp.name)
            segments, info = model.transcribe(tmp.name, beam_size=5)
            text = " ".join([seg.text for seg in segments])
            confidence = sum(seg.avg_logprob for seg in segments) / len(segments) if segments else 0
            return text, info.language, info.duration, confidence
        finally:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)

def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    for call_id, s3_uri in get_pending_calls():
        try:
            text, lang, dur, conf = transcribe_file(call_id, s3_uri)
            cur.execute("""
                INSERT INTO transcripts (recording_id, text, language, model_name, duration_seconds, confidence)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (recording_id) DO NOTHING;
            """, (call_id, text, lang, "faster-whisper-medium", dur, conf))
            mark_processed(cur, call_id, True)
            conn.commit()
        except Exception as e:
            mark_processed(cur, call_id, False, str(e))
            conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
