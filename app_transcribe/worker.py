#!/usr/bin/env python3
"""
Celery worker for audio transcription pipeline.

Consumes tasks from Redis, transcribes WAV files using OpenAI Whisper API,
stores results in PostgreSQL, and indexes in MeiliSearch.
"""

import os
import json
import tempfile
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor
import boto3
from openai import OpenAI
import meilisearch
from celery import Celery
from botocore.exceptions import ClientError

# =============================================================================
# Logging Configuration
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger(__name__)

# =============================================================================
# Celery Configuration
# =============================================================================
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
app = Celery("transcription", broker=REDIS_URL, backend=REDIS_URL)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)

# =============================================================================
# Database Configuration
# =============================================================================
PG_CONFIG = {
    'dbname': os.getenv("PGDATABASE"),
    'user': os.getenv("PGUSER"),
    'password': os.getenv("PGPASSWORD"),
    'host': os.getenv("PGHOST"),
    'port': os.getenv("PGPORT", "5432"),
}


def get_db_connection():
    """Create a new database connection."""
    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = False
    return conn


# =============================================================================
# S3/MinIO Configuration
# =============================================================================
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "192.168.1.152:9000")
MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "false").lower() == "true"
BUCKET = os.getenv("MINIO_BUCKET", "feeds")
BUCKET_PATH = os.getenv("AUDIO_BUCKET_PATH", "calls")

s3 = boto3.client(
    "s3",
    endpoint_url=f"http{'s' if MINIO_USE_SSL else ''}://{MINIO_ENDPOINT}",
    aws_access_key_id=os.getenv("MINIO_ROOT_USER"),
    aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD"),
)

# =============================================================================
# OpenAI Configuration
# =============================================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    log.warning("OPENAI_API_KEY not set - transcription will fail")

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

WHISPER_MODEL = "whisper-1"
LANGUAGE = os.getenv("LANGUAGE", "en")

# =============================================================================
# MeiliSearch Configuration
# =============================================================================
MEILI_HOST = os.getenv("MEILI_HOST", "http://meilisearch:7700")
MEILI_KEY = os.getenv("MEILI_MASTER_KEY")
meili_client = meilisearch.Client(MEILI_HOST, MEILI_KEY)
transcript_index = meili_client.index("transcripts")

# =============================================================================
# Helper Functions
# =============================================================================

def _extract_call_uid_from_key(s3_key: str) -> str:
    """Extract call_uid from S3 key path.

    Supports:
    - Hierarchical: calls/playlist_id=.../YYYY/MM/DD/call_{call_uid}.wav
    - Legacy flat: calls/{call_uid}.wav
    """
    match = re.search(r'call_([^/]+)\.wav$', s3_key)
    if match:
        return match.group(1)
    basename = os.path.basename(s3_key)
    return os.path.splitext(basename)[0]


def download_audio(s3_key: str, local_path: str) -> str:
    """Download audio file from S3 with fallback to legacy path.

    Returns the S3 key that was successfully used.
    """
    try:
        s3.download_file(BUCKET, s3_key, local_path)
        log.debug(f"Downloaded from primary path: {s3_key}")
        return s3_key
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code in ('404', 'NoSuchKey') or 'NoSuchKey' in str(e):
            call_uid = _extract_call_uid_from_key(s3_key)
            legacy_key = f"{BUCKET_PATH}/{call_uid}.wav"
            if legacy_key != s3_key:
                log.info(f"Fallback: trying legacy path {legacy_key}")
                s3.download_file(BUCKET, legacy_key, local_path)
                return legacy_key
        raise


def check_transcript_exists(conn, call_uid: str) -> bool:
    """Check if transcript already exists for this call_uid (idempotency)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM transcripts WHERE call_uid = %s LIMIT 1",
            (call_uid,)
        )
        return cur.fetchone() is not None


def calculate_confidence(segments: list) -> float:
    """Calculate average confidence from Whisper segments.

    Whisper provides avg_logprob per segment. Convert to 0-1 confidence.
    """
    if not segments:
        return 0.5  # Default confidence when no segments

    avg_logprob_values = [seg.get('avg_logprob', -0.5) for seg in segments if 'avg_logprob' in seg]
    if not avg_logprob_values:
        return 0.5

    avg_logprob = sum(avg_logprob_values) / len(avg_logprob_values)
    # avg_logprob is negative; typical range: -0.2 (excellent) to -1.5 (poor)
    # Convert to 0-1 scale
    confidence = (avg_logprob + 1.5) / 1.3
    return max(0.0, min(1.0, confidence))


def update_processing_state(conn, call_uid: str, status: str, error: str = None):
    """Update or insert processing state for a call."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO processing_state (call_uid, status, last_error, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (call_uid) DO UPDATE SET
                status = EXCLUDED.status,
                last_error = EXCLUDED.last_error,
                updated_at = NOW(),
                retry_count = CASE
                    WHEN EXCLUDED.status = 'error' THEN processing_state.retry_count + 1
                    ELSE processing_state.retry_count
                END
        """, (call_uid, status, error))


def insert_transcript(
    conn,
    call_uid: str,
    text: str,
    segments: list,
    language: str,
    duration_seconds: float,
    confidence: float,
    s3_key: str
) -> int:
    """Insert transcript into database. Returns the transcript ID."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO transcripts (
                call_uid, text, words, language, model_name,
                duration_seconds, confidence, s3_bucket, s3_key,
                created_at
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                NOW()
            )
            ON CONFLICT (call_uid) DO UPDATE SET
                text = EXCLUDED.text,
                words = EXCLUDED.words,
                language = EXCLUDED.language,
                model_name = EXCLUDED.model_name,
                duration_seconds = EXCLUDED.duration_seconds,
                confidence = EXCLUDED.confidence
            RETURNING id
        """, (
            call_uid,
            text,
            json.dumps(segments),
            language,
            WHISPER_MODEL,
            duration_seconds,
            confidence,
            BUCKET,
            s3_key,
        ))
        result = cur.fetchone()
        return result[0] if result else None


def index_to_meilisearch(transcript_id: int, call_uid: str, text: str, language: str):
    """Index transcript in MeiliSearch for full-text search."""
    try:
        transcript_index.add_documents([{
            "id": transcript_id,
            "call_uid": call_uid,
            "text": text,
            "language": language,
            "indexed_at": datetime.utcnow().isoformat()
        }])
        log.info(f"Indexed transcript {transcript_id} in MeiliSearch")
    except Exception as e:
        log.error(f"MeiliSearch indexing failed for {call_uid}: {e}")


def log_to_system_logs(conn, event_type: str, message: str, metadata: dict = None):
    """Log event to system_logs table."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO system_logs (component, event_type, message, metadata)
                VALUES (%s, %s, %s, %s)
            """, ('transcription', event_type, message, json.dumps(metadata or {})))
    except Exception as e:
        log.warning(f"Failed to log to system_logs: {e}")


def transcribe_with_openai(audio_path: str) -> Dict[str, Any]:
    """Call OpenAI Whisper API to transcribe audio.

    Returns dict with: text, segments, language, duration
    """
    if not openai_client:
        raise RuntimeError("OpenAI client not initialized - check OPENAI_API_KEY")

    with open(audio_path, "rb") as audio_file:
        response = openai_client.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=audio_file,
            language=LANGUAGE if LANGUAGE else None,
            response_format="verbose_json",
            timestamp_granularities=["segment"]
        )

    # Parse response - verbose_json returns a Transcription object
    result = {
        "text": response.text or "",
        "language": getattr(response, 'language', LANGUAGE) or LANGUAGE,
        "duration": getattr(response, 'duration', 0) or 0,
        "segments": []
    }

    # Extract segments if available
    if hasattr(response, 'segments') and response.segments:
        result["segments"] = [
            {
                "id": seg.id if hasattr(seg, 'id') else i,
                "start": seg.start if hasattr(seg, 'start') else 0,
                "end": seg.end if hasattr(seg, 'end') else 0,
                "text": seg.text if hasattr(seg, 'text') else "",
                "avg_logprob": getattr(seg, 'avg_logprob', -0.5),
                "no_speech_prob": getattr(seg, 'no_speech_prob', 0),
            }
            for i, seg in enumerate(response.segments)
        ]

    return result


# =============================================================================
# Celery Task
# =============================================================================

@app.task(
    name="transcription.transcribe",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(ClientError, psycopg2.OperationalError),
    retry_backoff=True,
    retry_backoff_max=300,
    acks_late=True
)
def transcribe(self, call_uid: str, s3_key: str) -> Dict[str, Any]:
    """
    Transcribe a single audio file using OpenAI Whisper API.

    Args:
        call_uid: Unique identifier for the call (bcfy_calls_raw.call_uid)
        s3_key: S3 object key for the WAV file

    Returns:
        Dict with transcript_id, call_uid, text length, confidence
    """
    task_id = self.request.id
    log.info(f"[{task_id}] Starting transcription for {call_uid}")

    conn = None
    tmp_path = None

    try:
        conn = get_db_connection()

        # Idempotency check
        if check_transcript_exists(conn, call_uid):
            log.info(f"[{task_id}] Transcript already exists for {call_uid}, skipping")
            update_processing_state(conn, call_uid, 'indexed')
            conn.commit()
            return {
                "status": "skipped",
                "reason": "already_exists",
                "call_uid": call_uid
            }

        # Update processing state to 'downloaded'
        update_processing_state(conn, call_uid, 'downloaded')
        conn.commit()

        # Download audio from S3
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        actual_s3_key = download_audio(s3_key, tmp_path)
        log.info(f"[{task_id}] Downloaded audio: {actual_s3_key}")

        # Transcribe with OpenAI Whisper API
        log.info(f"[{task_id}] Calling OpenAI Whisper API...")
        result = transcribe_with_openai(tmp_path)

        text = result["text"].strip()
        segments = result["segments"]
        language = result["language"]
        duration_seconds = result["duration"]

        # Calculate confidence from segments
        confidence = calculate_confidence(segments)

        log.info(f"[{task_id}] Transcribed: {len(text)} chars, {len(segments)} segments, "
                 f"duration={duration_seconds:.1f}s, confidence={confidence:.2f}")

        # Update processing state
        update_processing_state(conn, call_uid, 'transcribed')

        # Insert transcript
        transcript_id = insert_transcript(
            conn=conn,
            call_uid=call_uid,
            text=text,
            segments=segments,
            language=language,
            duration_seconds=duration_seconds,
            confidence=confidence,
            s3_key=actual_s3_key
        )

        log.info(f"[{task_id}] Inserted transcript {transcript_id} for {call_uid}")

        # Index in MeiliSearch
        index_to_meilisearch(transcript_id, call_uid, text, language)

        # Update processing state to indexed
        update_processing_state(conn, call_uid, 'indexed')

        # Log success
        log_to_system_logs(conn, 'transcription_complete', f"Transcribed {call_uid}", {
            'call_uid': call_uid,
            'transcript_id': transcript_id,
            'text_length': len(text),
            'segments': len(segments),
            'duration_seconds': duration_seconds,
            'confidence': confidence,
            'model': WHISPER_MODEL
        })

        conn.commit()

        return {
            "status": "success",
            "call_uid": call_uid,
            "transcript_id": transcript_id,
            "text_length": len(text),
            "segments": len(segments),
            "duration_seconds": duration_seconds,
            "confidence": confidence
        }

    except Exception as e:
        log.error(f"[{task_id}] Transcription failed for {call_uid}: {e}")

        if conn:
            try:
                conn.rollback()
                update_processing_state(conn, call_uid, 'error', str(e)[:500])
                log_to_system_logs(conn, 'transcription_error', str(e)[:200], {
                    'call_uid': call_uid,
                    'error_type': type(e).__name__,
                    'retry_count': self.request.retries
                })
                conn.commit()
            except Exception as log_err:
                log.error(f"[{task_id}] Failed to log error: {log_err}")

        raise

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

        if conn:
            try:
                conn.close()
            except Exception:
                pass


# =============================================================================
# Health Check Task
# =============================================================================

@app.task(name="transcription.health_check")
def health_check() -> Dict[str, Any]:
    """Health check task for monitoring."""
    return {
        "status": "healthy",
        "model": WHISPER_MODEL,
        "redis": REDIS_URL,
        "meili": MEILI_HOST,
        "bucket": BUCKET,
        "openai_configured": bool(OPENAI_API_KEY)
    }
