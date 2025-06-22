# Letterboxd Rating Tracker

A Flask application to track the average rating and rating count of films on Letterboxd over time. It scrapes film pages periodically and stores snapshots of the rating data, which can be viewed on a public dashboard with historical charts.

## Features

-   **Admin Dashboard**: Add, remove, and manage films to be tracked.
-   **Automated Scraping**: A background scheduler (APScheduler) periodically fetches new rating data for tracked films.
-   **Historical Data**: Stores rating snapshots to visualize trends over time.
-   **Public View**: A simple public interface to view tracked films and their rating history.
-   **API Endpoint**: Provides JSON data for charts.

## Tech Stack

-   **Backend**: Flask
-   **Database**: SQLAlchemy with SQLite (default) or PostgreSQL.
-   **Migrations**: Flask-Migrate
-   **Scheduling**: Flask-APScheduler
-   **Deployment**: Gunicorn, Nginx, Systemd

---

## Local Development Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd letterboxd-tracker
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    -   Copy the example environment file: `cp .env.example .env`
    -   Edit the `.env` file with your desired settings (admin credentials, secret key, etc.).

5.  **Initialize and migrate the database:**
    ```bash
    flask db init  # Only run this the very first time
    flask db migrate -m "Initial migration"
    flask db upgrade
    ```

6.  **Run the application:**
    ```bash
    flask run
    ```
    The app will be available at `http://127.0.0.1:5000`.

---

## Deployment

These instructions assume a Linux server (e.g., Ubuntu on Hetzner) with `python3`, `pip`, and `nginx` installed.

### 1. Initial Server Setup

Follow the "Local Development Setup" steps 1-4 on your server to clone the repo, create a virtual environment, install dependencies, and set up your production `.env` file.

### 2. Create `systemd` Service Files

You need **two** services: one for Gunicorn (the web app) and one for the scheduler.

#### A. Gunicorn Service

This will ensure Gunicorn runs as a background service and restarts automatically.

Create a file at `/etc/systemd/system/letterboxd-tracker.service`:
```ini
[Unit]
Description=Gunicorn instance to serve Letterboxd Tracker
After=network.target

[Service]
User=your_user
Group=www-data
WorkingDirectory=/path/to/your/letterboxd-tracker
Environment="PATH=/path/to/your/letterboxd-tracker/venv/bin"
ExecStart=/path/to/your/letterboxd-tracker/venv/bin/gunicorn --workers 3 --bind unix:letterboxd-tracker.sock -m 007 wsgi:app

[Install]
WantedBy=multi-user.target
```

#### B. Scheduler Service

This service runs the background scraping scheduler in a separate process.

Create a file at `/etc/systemd/system/letterboxd-tracker-scheduler.service`:
```ini
[Unit]
Description=Letterboxd Tracker Scheduler
After=network.target

[Service]
User=your_user
Group=www-data
WorkingDirectory=/path/to/your/letterboxd-tracker
Environment="PATH=/path/to/your/letterboxd-tracker/venv/bin"
ExecStart=/path/to/your/letterboxd-tracker/venv/bin/python run_scheduler.py

[Install]
WantedBy=multi-user.target
```

**Enable and start both services:**
```bash
sudo systemctl daemon-reload
sudo systemctl start letterboxd-tracker.service
sudo systemctl enable letterboxd-tracker.service
sudo systemctl start letterboxd-tracker-scheduler.service
sudo systemctl enable letterboxd-tracker-scheduler.service
```

**Check the status and logs for each service:**
```bash
sudo systemctl status letterboxd-tracker.service
sudo journalctl -u letterboxd-tracker.service -f

sudo systemctl status letterboxd-tracker-scheduler.service
sudo journalctl -u letterboxd-tracker-scheduler.service -f
```

> **Note:**  
> In production, the admin dashboard may display "Scheduler is running in a separate process" instead of the next scheduled scrape time.  
> To check the next scheduled run, use:
> ```bash
> sudo journalctl -u letterboxd-tracker-scheduler.service -f
> ```

### 3. Configure Nginx as a Reverse Proxy

Create a file at `/etc/nginx/sites-available/letterboxd-tracker`:
```nginx
server {
    listen 80;
    server_name your_domain www.your_domain;

    location / {
        include proxy_params;
        proxy_pass http://unix:/path/to/your/letterboxd-tracker/letterboxd-tracker.sock;
    }
}
```

**Enable the site and restart Nginx:**
```bash
sudo ln -s /etc/nginx/sites-available/letterboxd-tracker /etc/nginx/sites-enabled
sudo systemctl restart nginx
```

### 4. Deploying Updates

1.  SSH into your server and navigate to the project directory.
2.  Pull the latest code: `git pull`
3.  Update dependencies if needed: `pip install -r requirements.txt`
4.  Run database migrations if needed: `flask db upgrade`
5.  **Restart the Gunicorn service to apply changes:** `sudo systemctl restart letterboxd-tracker.service`
6.  Check the status and logs: `sudo systemctl status letterboxd-tracker.service` and `sudo journalctl -u letterboxd-tracker.service -f`

---

## Troubleshooting

- **Web app or scheduler service fails to start:**  
  Check the logs for errors:
  ```bash
  sudo journalctl -u letterboxd-tracker.service -f
  sudo journalctl -u letterboxd-tracker-scheduler.service -f
  ```
- **"Scheduler not running or job not found" in the dashboard:**  
  This is normal in production when the scheduler runs as a separate service. Use the logs to check the next scheduled run.
- **AssertionError about duplicate endpoints:**  
  Ensure `SCHEDULER_API_ENABLED` is set to `False` in `run_scheduler.py` and only `True` in your main app config.

- **Remember:**  
  Replace all `/path/to/your/letterboxd-tracker` and `your_user` placeholders with your actual paths and username.

---

