#!/bin/bash
# Auto-run nse.py every 5 minutes and push to GitHub
# Usage: ./run.sh (run once) or set up as cron job

cd "$(dirname "$0")"

echo "[$(date '+%H:%M:%S')] Running nse.py..."
python3 nse.py

if [ -f docs/nse_data.json ]; then
    STOCKS=$(python3 -c "import json; d=json.load(open('docs/nse_data.json')); print(d.get('count',0))")
    echo "[$(date '+%H:%M:%S')] Fetched $STOCKS stocks"

    if [ "$STOCKS" -gt "0" ]; then
        git add docs/nse_data.json
        git diff --staged --quiet || git commit -m "Update data $(date '+%Y-%m-%d %H:%M')"
        git push origin main 2>&1
        echo "[$(date '+%H:%M:%S')] Pushed to GitHub"
    else
        echo "[$(date '+%H:%M:%S')] No data (market closed?)"
    fi
else
    echo "[$(date '+%H:%M:%S')] ERROR: nse_data.json not created"
fi
