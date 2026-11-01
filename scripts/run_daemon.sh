#!/usr/bin/env bash
# GhostHire Background Daemon Launcher
cd "$(dirname "$0")/.."

PID_FILE="bot/ghosthire.pid"
LOG_FILE="bot/logs/ghosthire.log"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "GhostHire is already running with PID $(cat "$PID_FILE")."
    exit 0
fi

mkdir -p bot/logs
nohup python3 -u bot/runner.py --daemon >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "👻 GhostHire started in 24x7 background daemon mode (PID: $(cat "$PID_FILE"))."
echo "Logs: tail -f $LOG_FILE"

