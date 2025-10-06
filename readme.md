# Letterboxd Rating Tracker

A Flask application to track the average rating and rating count of films on Letterboxd over time. It scrapes film pages periodically and stores snapshots of the rating data, which can be viewed on a public dashboard with historical charts.

<img width="1336" height="828" alt="firefox_mPTWwuljps" src="https://github.com/user-attachments/assets/7f5820b6-9e96-477f-a293-eec3e889cf7f" />

## Features

-   **Admin Dashboard**: Add, remove, and manage films to be tracked.
-   **Automated Scraping**: A background scheduler (standalone APScheduler) periodically fetches new rating data for tracked films.
-   **Historical Data**: Stores rating snapshots to visualize trends over time.
-   **Public View**: A simple public interface to view tracked films and their rating history.
-   **API Endpoint**: Provides JSON data for charts.
-   **Manual Scraping**: Trigger immediate scraping from the admin dashboard.

## Tech Stack

-   **Backend**: Flask
-   **Database**: SQLAlchemy with SQLite (default) or PostgreSQL.
-   **Migrations**: Flask-Migrate
-   **Scheduling**: Standalone APScheduler (not Flask-APScheduler)
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
    Create a `.env` file in the project root with the following content:
    ```env
    # Flask Configuration
    SECRET_KEY=your-secret-key-here-change-this-in-production
    FLASK_ENV=development
    
    # Database Configuration (SQLite by default)
    DATABASE_URL=sqlite:///instance/letterboxd_tracker.sqlite3
    
    # Admin Dashboard Credentials
    ADMIN_USERNAME=admin
    ADMIN_PASSWORD=your-secure-password-here
    
    # Scheduler Configuration
    SCHEDULER_INTERVAL_MINUTES=60
    
    # Optional: Enable scheduler API in main Flask app
    SCHEDULER_API_ENABLED=False
    ```

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

## Running the Scheduler (NEW: Standalone Script)

The application now uses a **standalone APScheduler script** for scraping jobs. This is more robust and works reliably on all platforms.

### Local Development

Open a new terminal and run:
```bash
python run_scheduler.py
```
You should see output like:
```
Starting standalone APScheduler for scraping (interval: 15 min)...
Scheduler started! Press Ctrl+C to exit.
============================================================
SCHEDULED SCRAPE JOB FIRED at 2025-06-22 04:30:00
============================================================
```
The scraping job will run at the interval set in your `.env` file (`SCHEDULER_INTERVAL_MINUTES`).

### Production Deployment (systemd)

Create a systemd service for the scheduler:

`/etc/systemd/system/letterboxd-tracker-scheduler.service`
```ini
[Unit]
Description=Letterboxd Tracker Standalone Scheduler
After=network.target

[Service]
User=your_user
Group=www-data
WorkingDirectory=/path/to/your/letterboxd-tracker
Environment="PATH=/path/to/your/letterboxd-tracker/venv/bin"
ExecStart=/path/to/your/letterboxd-tracker/venv/bin/python run_scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable letterboxd-tracker-scheduler
sudo systemctl start letterboxd-tracker-scheduler
```

Check logs:
```bash
sudo journalctl -u letterboxd-tracker-scheduler -f
```

---

## Web App Deployment (Gunicorn + systemd)

Your web app is still deployed as before, using Gunicorn and systemd. Example service:

`/etc/systemd/system/letterboxd-tracker.service`
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

---

## Troubleshooting

- **Scheduler not running:**
  - Check the systemd service status: `sudo systemctl status letterboxd-tracker-scheduler`
  - Check logs: `sudo journalctl -u letterboxd-tracker-scheduler -f`
- **Web app issues:**
  - Check the Gunicorn service: `sudo systemctl status letterboxd-tracker`
  - Check logs: `sudo journalctl -u letterboxd-tracker -f`
- **Scheduler interval:**
  - Set `SCHEDULER_INTERVAL_MINUTES` in your `.env` file.
- **No scraping output:**
  - Make sure you are running `run_scheduler.py` and not the old Flask-APScheduler setup.

---

## Admin Dashboard

Access the admin dashboard at `http://127.0.0.1:5000/admin` and log in with your configured credentials.

**Features:**
- Add new films by Letterboxd URL
- Toggle tracking on/off for individual films
- Manual scraping for immediate updates
- View scheduler status and next run time
- Reorder films in the display list
- Delete films and their associated data

**Adding Films:**
1. Go to the film's page on Letterboxd (e.g., `https://letterboxd.com/film/28-years-later/`)
2. Copy the URL
3. Paste it into the "Add Film" form on the admin dashboard
4. The system will automatically extract the film slug and fetch initial data

---

## Development

### Testing the Scheduler

To test the scheduler manually:
```bash
python run_scheduler.py
```

### Checking Database Status

To check what films are in the database:
```bash
python debug_env.py
```

### Database Backup

Use the provided backup script:
```bash
./backup_db.sh
```

---

## License

This project is open source and available under the MIT License.

---
