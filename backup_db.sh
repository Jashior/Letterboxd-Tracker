#!/bin/bash
BACKUP_DIR="/home/dev/Letterboxd-Tracker/backups"
DB_PATH="/home/dev/Letterboxd-Tracker/instance/letterboxd_tracker.sqlite3"
DATE=$(date +"%Y-%m-%d_%H-%M-%S")
mkdir -p "$BACKUP_DIR"
cp "$DB_PATH" "$BACKUP_DIR/letterboxd_tracker_$DATE.sqlite3"
# Keep only the 4 most recent backups, delete the rest
ls -1t "$BACKUP_DIR"/letterboxd_tracker_*.sqlite3 | tail -n +5 | xargs rm -f