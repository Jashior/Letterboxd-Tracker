# Letterboxd Tracker – Update & Deployment Guide

## Website

[https://letterboxd-tracker.zanaris.dev](https://letterboxd-tracker.zanaris.dev)

---

## How to Deploy Updates

1. **Push your changes from your local machine:**
   ```bash
   git push
   ```

2. **On your Hetzner server, pull the latest changes:**
   ```bash
   cd /home/dev/Letterboxd-Tracker
   git pull
   ```

3. **Restart the Gunicorn service to apply updates:**
   ```bash
   sudo systemctl restart letterboxd-tracker
   ```

---

## Deployment Architecture Overview

- **Gunicorn**  
  Runs the Flask app as a production WSGI server.  
  Configured to listen on `127.0.0.1:5050` and managed by systemd.

- **Nginx**  
  Acts as a reverse proxy.  
  Forwards web traffic from `letterboxd-tracker.zanaris.dev` (port 80/443) to Gunicorn on port 5050.

- **systemd**  
  Manages the Gunicorn process as a service (`letterboxd-tracker.service`).  
  Ensures the app starts on boot and restarts if it crashes.  
  Restart the service after any code or template changes.

- **Backup Cron Jobs**  
  A cron job runs `/home/dev/Letterboxd-Tracker/backup_db.sh` weekly (Sunday 3am) to back up the SQLite database.  
  Only the 4 most recent backups are kept to save space.

---

## Useful Commands

- **Check service status:**
  ```bash
  sudo systemctl status letterboxd-tracker
  ```

- **View Nginx config:**
  ```bash
  sudo nano /etc/nginx/sites-available/letterboxd-tracker.zanaris.dev
  ```

- **List backups:**
  ```bash
  ls /home/dev/Letterboxd-Tracker/backups/
  ```

---

## Notes

- Nginx only needs to be reloaded if its configuration changes.
- Gunicorn/systemd must be restarted after code or template updates.
- Database backups are local; consider offsite/cloud backup for disaster recovery.

---