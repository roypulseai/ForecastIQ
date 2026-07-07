#!/usr/bin/env bash
# ForecastIQ - Stop native services (macOS / Linux)
set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

stopped=0
for pidfile in .backend.pid .frontend.pid; do
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" && echo "Stopped $pidfile (PID $pid)"
            stopped=$((stopped + 1))
        fi
        rm -f "$pidfile"
    fi
done

# Also kill anything listening on our ports (best effort)
for port in 3000 8000; do
    pids=$(lsof -ti:"$port" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "Killing leftover processes on port $port: $pids"
        kill -9 $pids 2>/dev/null || true
        stopped=$((stopped + 1))
    fi
done

if [ $stopped -eq 0 ]; then
    echo "No running services found."
else
    echo "Done."
fi
