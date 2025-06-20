#!/bin/bash

BACKUP_DIR="/home/dev/Letterboxd-Tracker/backups"
DB_PATH="/home/dev/Letterboxd-Tracker/instance/letterboxd_tracker.sqlite3"
DATE=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="$BACKUP_DIR/letterboxd_tracker_$DATE.sqlite3"

# Ensure the backup directory exists
mkdir -p "$BACKUP_DIR"

# Perform a safe SQLite backup
sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"

# Keep only the 4 most recent backups, delete the rest
ls -1t "$BACKUP_DIR"/letterboxd_tracker_*.sqlite3 | tail -n +5 | xargs -r rm -f
