#!/bin/bash

# Activate venv if used (commented out since you don't use one)
# source /opt/scanner/venv/bin/activate

cd /opt/scanner || exit 1

# Log file
LOGFILE="/opt/scanner/data/logs/scanner_service.log"

# Main scanner loop
while true; do
    echo "[$(date)] Running download_calls.py" >> "$LOGFILE"
    python3 download_calls.py >> "$LOGFILE" 2>&1
    sleep 3
done

