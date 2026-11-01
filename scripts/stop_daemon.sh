#!/usr/bin/env bash
# GhostHire Daemon Stop Script
cd "$(dirname "$0")/.."

PID_FILE="bot/ghosthire.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        echo "🛑 Stopped GhostHire (PID: $PID)."
    else
        echo "Process $PID not running."
    fi
    rm -f "$PID_FILE"
else
    echo "No running GhostHire instance found."
fi

