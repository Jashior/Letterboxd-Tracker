#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/backups"
DB_PATH="$SCRIPT_DIR/instance/letterboxd_tracker.sqlite3"
DATE=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="$BACKUP_DIR/letterboxd_tracker_$DATE.sqlite3"

# Ensure the backup directory exists
mkdir -p "$BACKUP_DIR"

# Check if database file exists
if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database file not found at $DB_PATH"
    exit 1
fi

# Perform a safe SQLite backup
echo "Creating backup: $BACKUP_FILE"
sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"

if [ $? -eq 0 ]; then
    echo "Backup completed successfully!"
    
    # Keep only the 5 most recent backups, delete the rest
    ls -1t "$BACKUP_DIR"/letterboxd_tracker_*.sqlite3 2>/dev/null | tail -n +6 | xargs -r rm -f
    
    echo "Backup files in $BACKUP_DIR:"
    ls -la "$BACKUP_DIR"/letterboxd_tracker_*.sqlite3 2>/dev/null || echo "No backup files found"
else
    echo "Backup failed!"
    exit 1
fi
