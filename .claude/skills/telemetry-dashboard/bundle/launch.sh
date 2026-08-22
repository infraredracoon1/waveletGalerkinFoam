#!/usr/bin/env bash
# Native launcher: starts the backend (FastAPI/uvicorn) and frontend (Node static
# server) locally, without Docker. Requires Python 3.9+ and Node.js 18+.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT="${TELEMETRY_BACKEND_PORT:-8000}"
FRONTEND_PORT="${TELEMETRY_FRONTEND_PORT:-3000}"

VENV="$DIR/backend/.venv"
if [ ! -d "$VENV" ]; then
  echo "Creating Python virtualenv..."
  python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install --quiet --disable-pip-version-check -r "$DIR/backend/requirements.txt"

echo "Starting backend on :$BACKEND_PORT ..."
(cd "$DIR/backend" && "$VENV/bin/uvicorn" main:app --host 0.0.0.0 --port "$BACKEND_PORT") &
BACKEND_PID=$!

echo "Starting frontend on :$FRONTEND_PORT ..."
(cd "$DIR/frontend" && TELEMETRY_FRONTEND_PORT="$FRONTEND_PORT" node server.js) &
FRONTEND_PID=$!

cleanup() {
  echo "Stopping telemetry dashboard..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo ""
echo "Telemetry Dashboard running:"
echo "  Frontend: http://localhost:$FRONTEND_PORT"
echo "  Backend:  http://localhost:$BACKEND_PORT"
echo ""
echo "Press Ctrl+C to stop."
wait
