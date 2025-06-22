import os
os.environ["RUNNING_SCHEDULER_PROCESS"] = "1"
os.environ["SCHEDULER_API_ENABLED"] = "False"  # <-- Add this line

from app import app
from scheduler import init_scheduler

if __name__ == "__main__":
    init_scheduler(app)
    print("Scheduler started. Press Ctrl+C to exit.")
    import time
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Scheduler stopped.")