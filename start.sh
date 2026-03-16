#!/bin/bash
cd ~/rude

# Kill anything on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null

# Start backend
uvicorn api:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Wait for it
echo "Starting backend..."
until curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; do sleep 0.5; done
echo "Backend ready."

# Start app
cd ~/rude/bfe-app
npm run tauri dev

# Cleanup
kill $BACKEND_PID 2>/dev/null
