# Letterboxd Tracker

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