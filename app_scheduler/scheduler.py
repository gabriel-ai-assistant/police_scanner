#!/usr/bin/env python3
"""
Unified Scheduler for Broadcastify Scanner Stack
Runs:
 • refresh_common() from get_cache_common_data.py once every 24 h
 • get_calls.py ingestion every 10 seconds
"""

import os
import subprocess
import logging
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from get_cache_common_data import refresh_common
from get_calls import ingest_loop
from audio_worker import process_pending_audio

# -----------------------------------------------------------------
# Setup
# -----------------------------------------------------------------
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("scheduler")

# -----------------------------------------------------------------
# Task: Refresh common Broadcastify data
# -----------------------------------------------------------------
async def job_refresh_common():
    log.info("🚀 Running job_refresh_common() ...")
    try:
        refresh_common()
        log.info("✅ refresh_common() completed successfully.")
    except Exception as e:
        log.exception(f"❌ refresh_common() failed: {e}")

# -----------------------------------------------------------------
# Task: Run ingestion (get_calls.py) - direct async call (no subprocess)
# -----------------------------------------------------------------
async def job_run_ingest():
    """Run ingestion directly (no subprocess overhead)."""
    log.info(f"🕒 Running ingestion at {datetime.now()}")
    try:
        await ingest_loop()
        log.info("✅ Ingestion completed.")
    except Exception as e:
        log.error(f"❌ Ingestion failed: {e}")

# -----------------------------------------------------------------
# Task: Process audio files
# -----------------------------------------------------------------
async def job_process_audio():
    """Process pending audio files in background."""
    try:
        await process_pending_audio()
    except Exception as e:
        log.error(f"❌ Audio processing failed: {e}")

# -----------------------------------------------------------------
# Scheduler Setup
# -----------------------------------------------------------------
async def main():
    sched = AsyncIOScheduler()

    # Daily refresh of cached metadata
    sched.add_job(job_refresh_common, "interval", hours=24, id="refresh_common")

    # Ingest calls every 10 seconds (with concurrency control)
    sched.add_job(job_run_ingest, "interval", seconds=10, id="run_ingest",
                  max_instances=1, coalesce=True)

    # Process audio files every 5 seconds (independent worker, with concurrency control)
    sched.add_job(
        job_process_audio,
        "interval",
        seconds=int(os.getenv("AUDIO_WORKER_INTERVAL_SEC", "5")),
        id="audio_worker",
        max_instances=1,
        coalesce=True
    )

    log.info("📅 Scheduler started — ingestion every 10 s, common refresh every 24 h")
    try:
        sched.start()
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        log.warning("🛑 Scheduler stopped manually.")

# -----------------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())
