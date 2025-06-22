# wsgi.py
# This file is used by Gunicorn for production deployment
from app import app

if __name__ == "__main__":
    app.run() 