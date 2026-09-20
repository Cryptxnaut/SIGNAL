#!/bin/bash
echo "Starting Signal..."

# Backend
cd backend
pip install -r requirements.txt --quiet
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# Frontend
cd frontend
npm install --silent
npm start &
FRONTEND_PID=$!
cd ..

echo "Signal running."
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  Ollama:   http://localhost:11434 (must be running separately)"
echo ""
echo "To connect ASUS GX10 LLM: ssh -L 11434:localhost:11434 user@<gx10-ip>"
echo "To use nRF54LM20: flash Zephyr firmware with BLE service UUID 12345678-1234-1234-1234-123456789abc"

wait $BACKEND_PID $FRONTEND_PID
