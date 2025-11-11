import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from jobs.get_cache_common_data import refresh_common  # updated import

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")

scheduler = BlockingScheduler()

# Refresh Broadcastify “common data” every night at 2 AM
scheduler.add_job(refresh_common, "cron", hour=2, minute=0)

if __name__ == "__main__":
    logging.info("Scheduler starting…")
    scheduler.start()
