#!/bin/bash
# AkpanBrain Infrastructure Guard — keeps API server + Cloudflare tunnel alive
# Checks every 30s, restarts if dead, updates tunnel URL in dashboard + redeploys Vercel
LOG="/config/brain/guard.log"
CURRENT_TUNNEL=""

while true; do
    # 1. API Server (port 8199)
    if ! curl -s -o /dev/null -w '' http://localhost:8199/api/agents 2>/dev/null; then
        echo "[$(date)] API server down — restarting..." >> "$LOG"
        pkill -f "python3 api_server.py" 2>/dev/null
        sleep 1
        cd /config/brain && python3 api_server.py >> /tmp/brain-api.log 2>&1 &
        sleep 3
    fi

    # 2. Cloudflare Tunnel
    if ! pgrep -f "cloudflared tunnel" > /dev/null 2>&1; then
        echo "[$(date)] Cloudflare tunnel down — restarting..." >> "$LOG"
        cloudflared tunnel --url http://localhost:8199 > /tmp/cf-out.log 2> /tmp/cf-err.log 2>&1 &
        sleep 8
        # Extract new tunnel URL
        NEW_URL=$(grep -oP 'https://[a-z-]+\.trycloudflare\.com' /tmp/cf-err.log 2>/dev/null | head -1)
        if [ -n "$NEW_URL" ] && [ "$NEW_URL" != "$CURRENT_TUNNEL" ]; then
            CURRENT_TUNNEL="$NEW_URL"
            echo "[$(date)] New tunnel URL: $NEW_URL" >> "$LOG"
            # Update dashboard HTML — put new URL first in TUNNELS array
            sed -i "s|const TUNNELS=\[.*\]|const TUNNELS=['$NEW_URL']|" /config/brain/dashboard/index.html
            # Redeploy to Vercel
            cd /config/brain && vercel deploy --prod --yes >> "$LOG" 2>&1
            echo "[$(date)] Dashboard redeployed with tunnel: $NEW_URL" >> "$LOG"
        fi
    fi

    # 3. Redis (port 6379)
    if ! redis-cli ping > /dev/null 2>&1; then
        echo "[$(date)] Redis down — restarting..." >> "$LOG"
        redis-server --daemonize yes --save "" --dir /tmp/ 2>/dev/null
    fi

    sleep 30
done
