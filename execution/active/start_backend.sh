#!/bin/bash
# Start the FastAPI backend server
# Logs are stored in ~/.tmp/backend.log

# Create log directory if it doesn't exist
mkdir -p ~/.tmp

# Change to backend directory
cd /root/surg-db/backend

# Start uvicorn with output redirected to ~/.tmp
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ~/.tmp/backend.log 2>&1 &

echo "Backend started. Logs: ~/.tmp/backend.log"
echo "PID: $!"
