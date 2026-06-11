#!/bin/bash
# One-time setup — installs everything, starts auto-fetcher
# Run this once: bash setup.sh

set -e

echo "=== NSE Data Fetcher Setup ==="

# Copy repo to home directory
DEST="/Users/ravivijnan/nse-data-fetcher"
if [ ! -d "$DEST" ]; then
    echo "Copying repo to $DEST..."
    cp -r "$(dirname "$0")" "$DEST"
else
    echo "Repo already at $DEST"
fi

cd "$DEST"

# Make scripts executable
chmod +x fetch_and_push.sh

# Copy launchd plist
cp com.nse.fetcher.plist ~/Library/LaunchAgents/

# Unload if already loaded
launchctl unload ~/Library/LaunchAgents/com.nse.fetcher.plist 2>/dev/null || true

# Load the service
launchctl load ~/Library/LaunchAgents/com.nse.fetcher.plist

echo ""
echo "=== Setup Complete ==="
echo "Auto-fetcher is now running!"
echo "It will:"
echo "  1. Check every 5 minutes"
echo "  2. Fetch NSE data during market hours (9:15 AM - 3:30 PM IST)"
echo "  3. Push to GitHub automatically"
echo ""
echo "Commands:"
echo "  Check status:  launchctl list | grep nse"
echo "  Stop:          launchctl unload ~/Library/LaunchAgents/com.nse.fetcher.plist"
echo "  Start:         launchctl load ~/Library/LaunchAgents/com.nse.fetcher.plist"
echo "  View logs:     tail -f $DEST/fetch.log"
echo ""
echo "GitHub: https://github.com/biranjan01/nse-data-fetcher"
echo "Vercel: https://nse-tracker-web.vercel.app"
