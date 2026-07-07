#!/usr/bin/env bash
# ForecastIQ - Setup WITHOUT Docker (macOS / Linux)
# Runs backend + frontend directly with native Python + Node.
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  ForecastIQ - Native Setup (no Docker)"
echo "========================================"
echo ""

# Check Python
if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
    echo "ERROR: Python 3.9+ is required."
    echo "macOS:   brew install python"
    echo "Ubuntu:  sudo apt-get install python3 python3-venv python3-pip"
    exit 1
fi

PY=$(command -v python3 || command -v python)
echo "Using Python: $($PY --version)"

# Check Node
if ! command -v node >/dev/null 2>&1; then
    echo "ERROR: Node.js 18+ is required."
    echo "macOS:   brew install node"
    echo "Ubuntu:  sudo apt-get install nodejs npm"
    exit 1
fi
echo "Using Node: $(node --version)"

# Backend setup
echo ""
echo "Setting up backend..."
cd "$SCRIPT_DIR/backend"

# Create venv if not present
if [ ! -d "venv" ]; then
    $PY -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# Start backend in background
echo "Starting backend on port 8000..."
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$SCRIPT_DIR/backend.log" 2>&1 &
echo $! > "$SCRIPT_DIR/.backend.pid"
echo "Backend PID: $(cat $SCRIPT_DIR/.backend.pid)"

# Frontend setup
echo ""
echo "Setting up frontend..."
cd "$SCRIPT_DIR/frontend"

if [ ! -d "node_modules" ]; then
    npm install --silent
fi

# Start frontend in background
echo "Starting frontend on port 3000..."
nohup npm run dev -- --host 0.0.0.0 --port 3000 > "$SCRIPT_DIR/frontend.log" 2>&1 &
echo $! > "$SCRIPT_DIR/.frontend.pid"
echo "Frontend PID: $(cat $SCRIPT_DIR/.frontend.pid)"

cd "$SCRIPT_DIR"
echo ""
echo "========================================"
echo "  ForecastIQ is starting!"
echo "========================================"
echo ""
echo "Frontend (UI):  http://localhost:3000"
echo "Backend (API):  http://localhost:8000"
echo "API Docs:       http://localhost:8000/docs"
echo ""
echo "Logs:"
echo "  Backend:  tail -f $SCRIPT_DIR/backend.log"
echo "  Frontend: tail -f $SCRIPT_DIR/frontend.log"
echo ""
echo "To stop:"
echo "  kill \$(cat $SCRIPT_DIR/.backend.pid)"
echo "  kill \$(cat $SCRIPT_DIR/.frontend.pid)"
echo ""
