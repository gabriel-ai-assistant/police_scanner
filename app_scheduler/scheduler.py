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
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv
from get_cache_common_data import refresh_common

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
def job_refresh_common():
    log.info("🚀 Running job_refresh_common() ...")
    try:
        refresh_common()
        log.info("✅ refresh_common() completed successfully.")
    except Exception as e:
        log.exception(f"❌ refresh_common() failed: {e}")

# -----------------------------------------------------------------
# Task: Run ingestion (get_calls.py)
# -----------------------------------------------------------------
def job_run_ingest():
    log.info(f"🕒 Triggering Broadcastify call ingestion at {datetime.now()}")
    try:
        subprocess.run(["python", "get_calls.py"], check=True)
        log.info("✅ Ingestion run completed successfully.")
    except subprocess.CalledProcessError as e:
        log.error(f"❌ Ingestion run failed: {e}")

# -----------------------------------------------------------------
# Scheduler Setup
# -----------------------------------------------------------------
def main():
    sched = BlockingScheduler()

    # Daily refresh of cached metadata
    sched.add_job(job_refresh_common, "interval", hours=24, id="refresh_common")

    # Ingest calls every 10 seconds
    sched.add_job(job_run_ingest, "interval", seconds=10, id="run_ingest")

    log.info("📅 Scheduler started — ingestion every 10 s, common refresh every 24 h")
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        log.warning("🛑 Scheduler stopped manually.")

# -----------------------------------------------------------------
if __name__ == "__main__":
    main()
