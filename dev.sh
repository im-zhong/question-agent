#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_CMD="uv run question-agent"
FRONTEND_CMD="npm run dev"

cleanup() {
  echo ""
  echo "Stopping servers..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  echo "Done."
}
trap cleanup EXIT INT TERM

# Start backend
echo "Starting backend (FastAPI :8000)..."
( cd "$ROOT_DIR" && $BACKEND_CMD ) &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend (Vite :5173)..."
( cd "$ROOT_DIR/frontend" && $FRONTEND_CMD ) &
FRONTEND_PID=$!

echo ""
echo "Both servers running. Press Ctrl+C to stop."
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo ""

wait -n "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
