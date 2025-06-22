# config.py
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'), override=True)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'letterboxd_tracker.sqlite3')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'password'
    SCHEDULER_API_ENABLED = False
    
    # Explicit Flask-APScheduler configuration
    SCHEDULER_JOBSTORES = {"default": {"type": "memory"}}
    SCHEDULER_EXECUTORS = {"default": {"type": "threadpool", "max_workers": 10}}
    SCHEDULER_JOB_DEFAULTS = {"coalesce": False, "max_instances": 1}
    SCHEDULER_TIMEZONE = "UTC"
    
    # More robustly handle potential inline comments from the .env file
    scheduler_interval_str = str(os.environ.get('SCHEDULER_INTERVAL_MINUTES', '60')).split('#')[0].strip()
    SCHEDULER_INTERVAL_MINUTES = int(scheduler_interval_str)

