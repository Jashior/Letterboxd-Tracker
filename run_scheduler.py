import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from app import app
from tasks import scheduled_scrape_task
from config import Config


def run_scrape_job():
    with app.app_context():
        print(f"\n{'='*60}")
        print(f"SCHEDULED SCRAPE JOB FIRED at {datetime.now()}")
        print(f"{'='*60}\n")
        scheduled_scrape_task()


def main():
    interval = getattr(Config, 'SCHEDULER_INTERVAL_MINUTES', 15)
    print(f"Starting standalone APScheduler for scraping (interval: {interval} min)...")
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=run_scrape_job,
        trigger='interval',
        minutes=interval,
        id='scrape_job',
        next_run_time=datetime.now()  # fire immediately on start
    )
    scheduler.start()
    print("Scheduler started! Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        scheduler.shutdown()
        print("Scheduler stopped.")

if __name__ == "__main__":
    main()