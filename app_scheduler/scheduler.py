#!/usr/bin/env python3
"""
Unified Scheduler for Broadcastify Scanner Stack
Runs:
 • refresh_common() from get_cache_common_data.py once every 24 h
 • get_calls.py ingestion every 10 seconds

Production features:
 • Graceful shutdown via SIGTERM/SIGINT — finishes current jobs before exiting
 • Health check HTTP endpoint on HEALTH_PORT (default 8088) for Docker healthchecks
 • Health file touch at /tmp/scheduler_healthy for file-based probes
"""

import os
import signal
import logging
import asyncio
from datetime import datetime
from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from get_cache_common_data import refresh_common
from get_calls import ingest_loop
from audio_worker import process_pending_audio
from transcription_dispatcher import dispatch_transcription_tasks
from db_pool import close_pool

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
# Graceful shutdown state
# -----------------------------------------------------------------
_shutdown_event: asyncio.Event = None  # set in main()
_active_jobs: int = 0                  # count of currently-running job coroutines
_active_jobs_lock: asyncio.Lock = None

HEALTH_FILE = os.getenv("HEALTH_FILE", "/tmp/scheduler_healthy")
HEALTH_PORT = int(os.getenv("HEALTH_PORT", "8088"))

def _is_shutting_down() -> bool:
    return _shutdown_event is not None and _shutdown_event.is_set()


async def _track_job(coro):
    """Wrapper that tracks active jobs for graceful shutdown."""
    global _active_jobs
    if _is_shutting_down():
        log.info(f"⏭️  Skipping job (shutdown in progress): {coro.__name__ if hasattr(coro, '__name__') else coro}")
        return
    async with _active_jobs_lock:
        _active_jobs += 1
    try:
        return await coro
    finally:
        async with _active_jobs_lock:
            _active_jobs -= 1


def _touch_health_file():
    """Touch health file to signal liveness to Docker / external probes."""
    try:
        with open(HEALTH_FILE, "w") as f:
            f.write(datetime.utcnow().isoformat())
    except Exception:
        pass  # Non-critical


def _remove_health_file():
    """Remove health file on shutdown."""
    try:
        if os.path.exists(HEALTH_FILE):
            os.remove(HEALTH_FILE)
    except Exception:
        pass

# -----------------------------------------------------------------
# Health check HTTP server
# -----------------------------------------------------------------
async def _health_handler(request):
    """HTTP health endpoint for Docker healthcheck."""
    if _is_shutting_down():
        return web.json_response(
            {"status": "shutting_down", "active_jobs": _active_jobs},
            status=503,
        )
    return web.json_response({
        "status": "healthy",
        "active_jobs": _active_jobs,
        "timestamp": datetime.utcnow().isoformat(),
    })


async def _start_health_server():
    """Start a lightweight HTTP health server."""
    app = web.Application()
    app.router.add_get("/health", _health_handler)
    app.router.add_get("/healthz", _health_handler)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", HEALTH_PORT)
    await site.start()
    log.info(f"🏥 Health endpoint listening on :{HEALTH_PORT}/health")
    return runner

# -----------------------------------------------------------------
# Task: Refresh common Broadcastify data
# -----------------------------------------------------------------
async def job_refresh_common():
    if _is_shutting_down():
        return
    log.info("🚀 Running job_refresh_common() ...")
    async def _run():
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, refresh_common)
    try:
        await _track_job(_run())
        log.info("✅ refresh_common() completed successfully.")
    except Exception as e:
        log.exception(f"❌ refresh_common() failed: {e}")
    _touch_health_file()

# -----------------------------------------------------------------
# Task: Run ingestion (get_calls.py) - direct async call (no subprocess)
# -----------------------------------------------------------------
async def job_run_ingest():
    """Run ingestion directly (no subprocess overhead)."""
    if _is_shutting_down():
        return
    log.info(f"🕒 Running ingestion at {datetime.now()}")
    try:
        await _track_job(ingest_loop())
        log.info("✅ Ingestion completed.")
    except Exception as e:
        log.error(f"❌ Ingestion failed: {e}")
    _touch_health_file()

# -----------------------------------------------------------------
# Task: Process audio files
# -----------------------------------------------------------------
async def job_process_audio():
    """Process pending audio files in background."""
    if _is_shutting_down():
        return
    try:
        await _track_job(process_pending_audio())
    except Exception as e:
        log.error(f"❌ Audio processing failed: {e}")
    _touch_health_file()

# -----------------------------------------------------------------
# Task: Dispatch transcription tasks to Celery
# -----------------------------------------------------------------
async def job_dispatch_transcriptions():
    """Queue pending transcription tasks to Celery workers."""
    if _is_shutting_down():
        return
    try:
        count = await _track_job(dispatch_transcription_tasks())
        if count and count > 0:
            log.info(f"📝 Dispatched {count} transcription tasks")
    except Exception as e:
        log.error(f"❌ Transcription dispatch failed: {e}")
    _touch_health_file()

# -----------------------------------------------------------------
# Scheduler Setup
# -----------------------------------------------------------------
async def main():
    global _shutdown_event, _active_jobs_lock
    _shutdown_event = asyncio.Event()
    _active_jobs_lock = asyncio.Lock()

    loop = asyncio.get_running_loop()
    sched = AsyncIOScheduler()

    # ------ Signal handlers for graceful shutdown ------
    def _request_shutdown(sig):
        sig_name = signal.Signals(sig).name
        log.warning(f"🛑 Received {sig_name} — initiating graceful shutdown...")
        _shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _request_shutdown, sig)

    # ------ Start health check HTTP server ------
    health_runner = await _start_health_server()
    _touch_health_file()

    # ------ Schedule jobs ------
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

    # Dispatch transcription tasks every 30 seconds
    sched.add_job(
        job_dispatch_transcriptions,
        "interval",
        seconds=int(os.getenv("TRANSCRIPTION_DISPATCH_INTERVAL_SEC", "30")),
        id="transcription_dispatcher",
        max_instances=1,
        coalesce=True
    )

    log.info("📅 Scheduler started — ingestion every 10 s, audio every 5 s, transcription every 30 s")
    sched.start()

    # ------ Wait for shutdown signal ------
    await _shutdown_event.wait()

    # ------ Graceful shutdown sequence ------
    log.info("⏳ Stopping scheduler (no new jobs will fire)...")
    sched.shutdown(wait=False)  # stop firing new jobs

    # Wait for in-flight jobs to finish (up to 30 s)
    shutdown_timeout = int(os.getenv("SHUTDOWN_TIMEOUT_SEC", "30"))
    log.info(f"⏳ Waiting up to {shutdown_timeout}s for {_active_jobs} active job(s) to finish...")
    waited = 0
    while _active_jobs > 0 and waited < shutdown_timeout:
        await asyncio.sleep(1)
        waited += 1
        if waited % 5 == 0:
            log.info(f"   ... still waiting ({_active_jobs} active, {waited}s elapsed)")

    if _active_jobs > 0:
        log.warning(f"⚠️  Shutdown timeout reached with {_active_jobs} job(s) still running — exiting anyway")
    else:
        log.info("✅ All jobs finished cleanly.")

    # Clean up resources
    _remove_health_file()
    await health_runner.cleanup()
    await close_pool()
    log.info("👋 Scheduler exited gracefully.")

# -----------------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())
