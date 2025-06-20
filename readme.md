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

### 2. Create a `systemd` Service File

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

**Enable and start the service:**
```bash
sudo systemctl start letterboxd-tracker.service
sudo systemctl enable letterboxd-tracker.service
```

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