#!/usr/bin/env python3
"""
Minimal test to verify APScheduler is working
"""
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

def test_job():
    print(f"\n{'='*50}")
    print(f"TEST JOB EXECUTED at {datetime.now()}")
    print(f"{'='*50}\n")
    import sys; sys.stdout.flush()

def main():
    print("Starting minimal APScheduler test...")
    
    # Create scheduler
    scheduler = BackgroundScheduler()
    
    # Add a job that runs every 30 seconds
    job = scheduler.add_job(
        func=test_job,
        trigger='interval',
        seconds=30,
        id='test_job'
    )
    
    print(f"Added test job with ID: {job.id}")
    
    # Start the scheduler
    scheduler.start()
    print("Scheduler started!")
    
    try:
        # Keep running
        while True:
            time.sleep(10)
            print(f"Main loop: {datetime.now()} - Scheduler running: {scheduler.running}")
            import sys; sys.stdout.flush()
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        scheduler.shutdown()
        print("Scheduler stopped.")

if __name__ == "__main__":
    main() 