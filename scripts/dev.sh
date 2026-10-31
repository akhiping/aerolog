#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

echo "=== AeroLog Development Server ==="
echo ""

# Install Python dependencies
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null

# Copy .env if needed
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
fi

# Run seed if DB doesn't exist
if [ ! -f "aerolog.db" ]; then
    echo "Seeding database..."
    python seed.py
fi

# Install frontend dependencies
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd frontend && npm install && cd ..
fi

echo ""
echo "Starting backend (port 8000) and frontend (port 5173)..."
echo "  API docs:    http://localhost:8000/docs"
echo "  Technician:  http://localhost:5173/"
echo "  Dashboard:   http://localhost:5173/dashboard"
echo ""

# Start both
(cd frontend && npm run dev &)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
