#!/usr/bin/env python3
"""
Background worker to process unprocessed audio files.
Runs independently of ingestion cycle for near-real-time processing.

This worker:
1. Finds calls with processed=FALSE in the database
2. Downloads MP3 from Broadcastify URL
3. Converts to optimized WAV using FFmpeg + librosa
4. Uploads to MinIO
5. Updates database with S3 URL and processed=TRUE
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

async def process_pending_audio():
    """Process calls with processed=FALSE, with retry logic and feature flag support."""
    conn = await get_connection()
    try:
        # Get unprocessed calls (oldest first)
        calls = await conn.fetch("""
            SELECT call_uid, url, raw_json
            FROM bcfy_calls_raw
            WHERE processed = FALSE AND error IS NULL
            ORDER BY fetched_at ASC
            LIMIT $1
        """, BATCH_SIZE)

        if not calls:
            log.debug("No pending audio files")
            return

        log.info(f"Processing {len(calls)} pending audio files... "
                f"[Enhanced: {USE_ENHANCED_PROCESSING}]")

        async with aiohttp.ClientSession() as session:
            for call in calls:
                call_uid = call['call_uid']
                src_url = call['url']

                # Attempt processing with retries
                success = False
                last_error = None

                for attempt in range(MAX_RETRIES + 1):
                    try:
                        # Download, convert, upload
                        s3_url = await store_audio(session, src_url, call_uid)

                        # Update with S3 location
                        await conn.execute("""
                            UPDATE bcfy_calls_raw
                            SET url = $1, processed = TRUE, last_attempt = NOW()
                            WHERE call_uid = $2
                        """, s3_url, call_uid)

                        log.info(f"✓ Processed {call_uid} "
                                f"(attempt {attempt + 1}/{MAX_RETRIES + 1})")
                        success = True
                        break

                    except Exception as e:
                        last_error = e
                        if attempt < MAX_RETRIES:
                            # Calculate exponential backoff
                            backoff_sec = RETRY_BACKOFF_BASE ** attempt
                            log.warning(f"✗ Attempt {attempt + 1}/{MAX_RETRIES + 1} "
                                       f"failed for {call_uid}: {str(e)[:100]}")
                            log.info(f"  Retrying in {backoff_sec}s...")
                            await asyncio.sleep(backoff_sec)
                        else:
                            log.error(f"✗ Failed {call_uid} after {MAX_RETRIES + 1} attempts")

                # If all retries exhausted, mark error
                if not success and last_error:
                    # Extract clean error message without S3 paths
                    error_msg = str(last_error).split('s3://')[0] if 's3://' in str(last_error) else str(last_error)
                    error_type = type(last_error).__name__
                    clean_error = f"{error_type}: {error_msg.strip()}"[:500]

                    # Mark error for manual intervention or later processing
                    await conn.execute("""
                        UPDATE bcfy_calls_raw
                        SET error = $1, last_attempt = NOW()
                        WHERE call_uid = $2
                    """, clean_error, call_uid)

                    log.error(f"✗ Error logged: {clean_error}")

    except Exception as e:
        log.exception(f"Fatal error in audio processing loop: {e}")
    finally:
        await release_connection(conn)

if __name__ == "__main__":
    log.info("Starting audio worker...")
    try:
        asyncio.run(process_pending_audio())
    except Exception as e:
        log.exception(f"Fatal error: {e}")
