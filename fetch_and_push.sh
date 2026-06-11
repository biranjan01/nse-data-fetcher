#!/bin/bash
# NSE Data Fetcher — runs every 5 min via launchd
# Fetches NSE option chain data and pushes to GitHub

cd /Users/ravivijnan/nse-data-fetcher

LOGFILE="fetch.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOGFILE"
}

# Check if market is open (9:15 AM - 3:30 PM IST, Mon-Fri)
IST_HOUR=$(python3 -c "
from datetime import datetime, timezone, timedelta
ist = timezone(timedelta(hours=5, minutes=30))
now = datetime.now(ist)
print(now.hour)
")
IST_MIN=$(python3 -c "
from datetime import datetime, timezone, timedelta
ist = timezone(timedelta(hours=5, minutes=30))
now = datetime.now(ist)
print(now.minute)
")
DOW=$(python3 -c "
from datetime import datetime, timezone, timedelta
ist = timezone(timedelta(hours=5, minutes=30))
now = datetime.now(ist)
print(now.weekday())
")

IST_TOTAL=$((IST_HOUR * 60 + IST_MIN))

if [ "$DOW" -ge 5 ]; then
    exit 0
fi

if [ "$IST_TOTAL" -lt 555 ] || [ "$IST_TOTAL" -gt 930 ]; then
    exit 0
fi

log "Starting fetch..."
python3 nse.py >> "$LOGFILE" 2>&1

if [ -f docs/nse_data.json ]; then
    STOCKS=$(python3 -c "import json; d=json.load(open('docs/nse_data.json')); print(d.get('count',0))")
    log "Fetched $STOCKS stocks"

    if [ "$STOCKS" -gt "0" ]; then
        git add docs/nse_data.json
        git diff --staged --quiet || {
            git commit -m "Update data $(date '+%Y-%m-%d %H:%M')"
            git push origin main >> "$LOGFILE" 2>&1
            log "Pushed to GitHub"
        }
    fi
fi

# Keep log file small (last 500 lines)
if [ -f "$LOGFILE" ]; then
    tail -500 "$LOGFILE" > "$LOGFILE.tmp" && mv "$LOGFILE.tmp" "$LOGFILE"
fi
