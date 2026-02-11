#!/usr/bin/env python3
"""
Background worker to process unprocessed audio files.
Runs independently of ingestion cycle for near-real-time processing.

This worker:
1. Claims a batch of calls by setting status='processing' in a short transaction
2. Downloads MP3 from Broadcastify URL (outside any transaction/lock)
3. Converts to optimized WAV using FFmpeg + librosa
4. Uploads to MinIO
5. Updates database with S3 URL and status='completed'

Lock strategy: SELECT FOR UPDATE SKIP LOCKED is used only briefly to claim rows.
The lock is released immediately after setting status='processing'. All long I/O
(download/convert/upload) happens outside the transaction so crashes don't leave
rows locked — they stay in 'processing' and get recovered by recover_stuck_jobs().
"""

import asyncio
import aiohttp
import os
import logging
from dotenv import load_dotenv
from db_pool import get_connection, release_connection
from get_calls import store_audio

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)

BATCH_SIZE = int(os.getenv("AUDIO_WORKER_BATCH_SIZE", "20"))
MAX_RETRIES = int(os.getenv("AUDIO_WORKER_MAX_RETRIES", "2"))
RETRY_BACKOFF_BASE = 2  # Exponential backoff: 2^attempt seconds
USE_ENHANCED_PROCESSING = os.getenv("AUDIO_USE_ENHANCED_PROCESSING", "false").lower() == "true"
STUCK_JOB_TIMEOUT_MIN = int(os.getenv("AUDIO_WORKER_STUCK_TIMEOUT_MIN", "10"))


async def recover_stuck_jobs():
    """Reset rows stuck in 'processing' for longer than STUCK_JOB_TIMEOUT_MIN back to 'pending'.

    This handles cases where a worker crashes mid-processing. Since we commit
    status='processing' before doing I/O, a crash leaves the row in 'processing'
    rather than row-locked, making recovery straightforward.
    """
    conn = await get_connection()
    try:
        result = await conn.execute("""
            UPDATE bcfy_calls_raw
            SET status = 'pending', picked_at = NULL
            WHERE status = 'processing'
              AND picked_at < NOW() - INTERVAL '$1 minutes'
        """.replace("$1", str(STUCK_JOB_TIMEOUT_MIN)))
        rows = int(result.split()[-1])
        if rows > 0:
            log.warning(f"Recovered {rows} stuck job(s) (processing > {STUCK_JOB_TIMEOUT_MIN}min)")
    except Exception as e:
        log.exception(f"Error recovering stuck jobs: {e}")
    finally:
        await release_connection(conn)


async def claim_pending_batch():
    """Claim a batch of pending rows using a short-lived lock, then release immediately.

    Returns the list of claimed call records (as dicts).
    """
    conn = await get_connection()
    try:
        # Short transaction: lock rows, set status='processing', commit, release lock
        async with conn.transaction():
            calls = await conn.fetch("""
                SELECT call_uid, url, raw_json, playlist_uuid, started_at,
                       tg_id, duration_ms, feed_id
                FROM bcfy_calls_raw
                WHERE status = 'pending' AND error IS NULL
                ORDER BY fetched_at ASC
                LIMIT $1
                FOR UPDATE SKIP LOCKED
            """, BATCH_SIZE)

            if not calls:
                return []

            call_uids = [c['call_uid'] for c in calls]
            await conn.execute("""
                UPDATE bcfy_calls_raw
                SET status = 'processing', picked_at = NOW()
                WHERE call_uid = ANY($1)
            """, call_uids)

        # Transaction committed — locks released. Return plain dicts.
        return [dict(c) for c in calls]
    finally:
        await release_connection(conn)


async def mark_completed(call_uid: str, s3_uri: str, s3_key: str):
    """Mark a row as completed after successful I/O."""
    conn = await get_connection()
    try:
        result = await conn.execute("""
            UPDATE bcfy_calls_raw
            SET url = $1, s3_key_v2 = $2, processed = TRUE,
                status = 'completed', last_attempt = NOW()
            WHERE call_uid = $3
        """, s3_uri, s3_key, call_uid)
        rows_affected = int(result.split()[-1])
        if rows_affected != 1:
            log.error(f"UPDATE affected {rows_affected} rows for {call_uid}, expected 1")
        else:
            log.debug(f"UPDATE verified: 1 row affected for {call_uid}")
    finally:
        await release_connection(conn)


async def mark_failed(call_uid: str, error_msg: str):
    """Mark a row as failed after exhausting retries."""
    conn = await get_connection()
    try:
        await conn.execute("""
            UPDATE bcfy_calls_raw
            SET error = $1, status = 'failed', last_attempt = NOW()
            WHERE call_uid = $2
        """, error_msg[:500], call_uid)
    finally:
        await release_connection(conn)


async def process_pending_audio():
    """Process calls with status='pending', with retry logic and feature flag support."""

    # First, recover any stuck jobs from prior crashes
    await recover_stuck_jobs()

    # Claim a batch (short lock, immediately released)
    calls = await claim_pending_batch()

    if not calls:
        log.debug("No pending audio files")
        return

    log.info(f"Processing {len(calls)} pending audio files... "
             f"[Enhanced: {USE_ENHANCED_PROCESSING}]")

    # All I/O happens here — no database locks held
    async with aiohttp.ClientSession() as session:
        for call in calls:
            call_uid = call['call_uid']
            src_url = call['url']

            call_metadata = {
                'playlist_uuid': call['playlist_uuid'],
                'started_at': call['started_at'],
                'tg_id': call['tg_id'],
                'duration_ms': call['duration_ms'],
                'feed_id': call['feed_id']
            }

            success = False
            last_error = None

            for attempt in range(MAX_RETRIES + 1):
                try:
                    s3_key, s3_uri = await store_audio(session, src_url, call_uid, call_metadata)
                    await mark_completed(call_uid, s3_uri, s3_key)

                    log.info(f"✓ Processed {call_uid} "
                             f"(attempt {attempt + 1}/{MAX_RETRIES + 1})")
                    success = True
                    break

                except Exception as e:
                    last_error = e
                    if attempt < MAX_RETRIES:
                        backoff_sec = RETRY_BACKOFF_BASE ** attempt
                        log.warning(f"✗ Attempt {attempt + 1}/{MAX_RETRIES + 1} "
                                    f"failed for {call_uid}: {str(e)[:100]}")
                        log.info(f"  Retrying in {backoff_sec}s...")
                        await asyncio.sleep(backoff_sec)
                    else:
                        log.error(f"✗ Failed {call_uid} after {MAX_RETRIES + 1} attempts")

            if not success and last_error:
                error_msg = str(last_error).split('s3://')[0] if 's3://' in str(last_error) else str(last_error)
                error_type = type(last_error).__name__
                clean_error = f"{error_type}: {error_msg.strip()}"
                await mark_failed(call_uid, clean_error)
                log.error(f"✗ Error logged: {clean_error[:200]}")


if __name__ == "__main__":
    log.info("Starting audio worker...")
    try:
        asyncio.run(process_pending_audio())
    except Exception as e:
        log.exception(f"Fatal error: {e}")
