import os
os.environ["RUNNING_SCHEDULER_PROCESS"] = "1"
os.environ["SCHEDULER_API_ENABLED"] = "False"  # <-- Add this line
print("RUN_SCHEDULER: SCHEDULER_INTERVAL_MINUTES =", os.environ.get("SCHEDULER_INTERVAL_MINUTES"))

from app import app
from scheduler import init_scheduler

if __name__ == "__main__":
    # We need to run this within the application context so that the
    # scheduler's jobs have access to the app's configuration and extensions.
    with app.app_context():
        init_scheduler(app)
        print("Scheduler started. Press Ctrl+C to exit.")
        import time
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("Scheduler stopped.")