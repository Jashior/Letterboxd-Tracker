import os
from dotenv import load_dotenv

print("Before loading .env:")
print(f"SCHEDULER_INTERVAL_MINUTES = {os.environ.get('SCHEDULER_INTERVAL_MINUTES')}")

# Clear the environment variable
if 'SCHEDULER_INTERVAL_MINUTES' in os.environ:
    del os.environ['SCHEDULER_INTERVAL_MINUTES']
    print("Cleared SCHEDULER_INTERVAL_MINUTES from environment")

# Load .env file
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')
print(f"\nLoading .env from: {env_path}")
print(f"File exists: {os.path.exists(env_path)}")

if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        print("Contents of .env file:")
        for line in f:
            print(f"  {line.strip()}")

load_dotenv(env_path, override=True)

print(f"\nAfter loading .env:")
print(f"SCHEDULER_INTERVAL_MINUTES = {os.environ.get('SCHEDULER_INTERVAL_MINUTES')}")

# Test config loading
from config import Config
print(f"\nConfig values:")
print(f"SCHEDULER_INTERVAL_MINUTES = {Config.SCHEDULER_INTERVAL_MINUTES}")

# Test app config
from app import app
with app.app_context():
    print(f"\nApp config:")
    print(f"SCHEDULER_INTERVAL_MINUTES = {app.config.get('SCHEDULER_INTERVAL_MINUTES')}") 