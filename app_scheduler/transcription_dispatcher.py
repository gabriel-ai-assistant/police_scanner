#!/usr/bin/env python3
"""
Transcription task dispatcher.

Queries for processed audio files without transcripts and queues Celery tasks
to the transcription worker.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

from celery import Celery
from db_pool import get_connection, release_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)

# Celery app for queueing (must match worker configuration)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery_app = Celery("transcription", broker=REDIS_URL)

# Configuration
BATCH_SIZE = int(os.getenv("TRANSCRIPTION_BATCH_SIZE", "10"))
MAX_AGE_HOURS = int(os.getenv("TRANSCRIPTION_MAX_AGE_HOURS", "72"))
RATE_LIMIT_DELAY = float(os.getenv("TRANSCRIPTION_RATE_LIMIT_DELAY", "0.5"))


async def get_pending_transcriptions(conn, batch_size: int, max_age_hours: int) -> List[Dict[str, Any]]:
    """
    Query for calls that need transcription.

    Criteria:
    - processed = TRUE (WAV file in S3)
    - s3_key_v2 IS NOT NULL (has hierarchical key)
    - No matching transcript exists
    - Not too old (within max_age_hours)
    - No active error in processing_state (or error with retries available)
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

    rows = await conn.fetch("""
        SELECT
            c.call_uid,
            c.s3_key_v2,
            c.started_at,
            c.duration_ms,
            c.playlist_uuid,
            ps.status as processing_status,
            ps.retry_count
        FROM bcfy_calls_raw c
        LEFT JOIN transcripts t ON c.call_uid = t.call_uid
        LEFT JOIN processing_state ps ON c.call_uid = ps.call_uid
        WHERE
            c.processed = TRUE
            AND c.s3_key_v2 IS NOT NULL
            AND c.error IS NULL
            AND t.id IS NULL
            AND c.started_at > $1
            AND (
                ps.status IS NULL
                OR (ps.status = 'error' AND COALESCE(ps.retry_count, 0) < COALESCE(ps.max_retries, 3))
                OR ps.status NOT IN ('transcribed', 'indexed', 'error')
            )
        ORDER BY c.started_at DESC
        LIMIT $2
    """, cutoff_time, batch_size)

    return [dict(row) for row in rows]


async def queue_transcription_task(call_uid: str, s3_key: str) -> str:
    """
    Queue a transcription task via Celery.

    Returns the Celery task ID.
    """
    result = celery_app.send_task(
        'transcription.transcribe',
        args=[call_uid, s3_key],
        queue='celery',
        retry=False
    )
    return result.id


async def dispatch_transcription_tasks() -> int:
    """
    Main dispatcher function.

    Queries pending transcriptions and queues Celery tasks.
    Returns the number of tasks queued.
    """
    conn = await get_connection()
    queued_count = 0

    try:
        pending = await get_pending_transcriptions(conn, BATCH_SIZE, MAX_AGE_HOURS)

        if not pending:
            log.debug("No pending transcriptions")
            return 0

        log.info(f"Found {len(pending)} calls pending transcription")

        for call in pending:
            call_uid = call['call_uid']
            s3_key = call['s3_key_v2']

            try:
                # Initialize processing_state if not exists
                await conn.execute("""
                    INSERT INTO processing_state (call_uid, status, updated_at)
                    VALUES ($1, 'queued', NOW())
                    ON CONFLICT (call_uid) DO UPDATE SET
                        status = 'queued',
                        updated_at = NOW()
                """, call_uid)

                # Queue the task
                task_id = await queue_transcription_task(call_uid, s3_key)
                queued_count += 1

                log.info(f"Queued transcription for {call_uid} (task: {task_id})")

                # Rate limiting
                await asyncio.sleep(RATE_LIMIT_DELAY)

            except Exception as e:
                log.error(f"Failed to queue {call_uid}: {e}")
                continue

        # Log batch completion
        if queued_count > 0:
            await conn.execute("""
                INSERT INTO system_logs (component, event_type, message, metadata)
                VALUES ($1, $2, $3, $4::jsonb)
            """, 'transcription_dispatcher', 'batch_queued',
                f"Queued {queued_count}/{len(pending)} transcription tasks",
                f'{{"queued": {queued_count}, "total": {len(pending)}}}')

        log.info(f"Queued {queued_count} transcription tasks")
        return queued_count

    except Exception as e:
        log.exception(f"Dispatcher error: {e}")
        return 0

    finally:
        await release_connection(conn)


if __name__ == "__main__":
    asyncio.run(dispatch_transcription_tasks())
