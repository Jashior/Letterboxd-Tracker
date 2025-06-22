# config.py
import os
from dotenv import load_dotenv
print("ENV SCHEDULER_INTERVAL_MINUTES =", os.environ.get("SCHEDULER_INTERVAL_MINUTES"))

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'letterboxd_tracker.sqlite3')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'password'
    SCHEDULER_API_ENABLED = False
    # More robustly handle potential inline comments from the .env file
    scheduler_interval_str = str(os.environ.get('SCHEDULER_INTERVAL_MINUTES', '60')).split('#')[0].strip()
    SCHEDULER_INTERVAL_MINUTES = int(scheduler_interval_str)

