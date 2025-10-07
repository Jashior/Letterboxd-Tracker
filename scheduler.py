# scheduler.py
from flask_apscheduler import APScheduler
from datetime import datetime, timedelta
import logging
import sys; sys.stdout.flush()
logging.info("APScheduler initialized.")

from tasks import scheduled_scrape_task # Import the task from our new file

logger = logging.getLogger(__name__)
scheduler = APScheduler()

SCRAPE_JOB_ID = "scrape_letterboxd_ratings"

def hello_test_job():
    """Simple test job to verify scheduler is working"""
    logger.info("Hello world test job fired")

def init_scheduler(app):
    """Initializes and starts the APScheduler."""
    # This function is called from app.py to start the scheduler.
    if not scheduler.running:
        scheduler.init_app(app)
        scheduler.start()
        logger.info("Scheduler started and should be running jobs.")
        logger.info("APScheduler initialized and started.")

        # Add a simple test job first
        test_job = scheduler.add_job(
            id="hello_test_job",
            func=hello_test_job,
            trigger='interval',
            seconds=30,
            replace_existing=True
        )
        logger.info("Test job added with ID: hello_test_job")

        # Check if job already exists to prevent duplicates on app restart
        if not scheduler.get_job(SCRAPE_JOB_ID):
            interval_minutes = int(app.config.get('SCHEDULER_INTERVAL_MINUTES', 60))
            logger.debug(f"interval_minutes = {interval_minutes} (type: {type(interval_minutes)})")
            job = scheduler.add_job(
                id=SCRAPE_JOB_ID,
                func=scheduled_scrape_task,
                trigger='interval',
                minutes=interval_minutes,
                next_run_time=datetime.now() + timedelta(seconds=10) # Start 10s after app start
            )
            logger.info(f"Scheduled scrape job to run every {interval_minutes} minutes.")
            if hasattr(job, 'next_run_time') and job.next_run_time:
                logger.info(f"Next scheduled run is at: {job.next_run_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            logger.info(f"Job added with ID: {SCRAPE_JOB_ID}")
        else:
            logger.info("Scrape job already exists; not adding duplicate.")
    else:
        logger.info("APScheduler already running.")