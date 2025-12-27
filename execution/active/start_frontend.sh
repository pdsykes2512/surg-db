#!/bin/bash
# Start the Vite frontend development server
# Logs are stored in ~/.tmp/frontend.log

# Create log directory if it doesn't exist
mkdir -p ~/.tmp

# Change to frontend directory
cd /root/frontend

# Start vite with host binding and output redirected to ~/.tmp
npm run dev -- --host 0.0.0.0 > ~/.tmp/frontend.log 2>&1 &

echo "Frontend started. Logs: ~/.tmp/frontend.log"
echo "PID: $!"
