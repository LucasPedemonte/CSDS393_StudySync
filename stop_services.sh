#!/bin/bash
# Stop Backend and Frontend services

echo "🛑 Stopping StudySync services..."

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Stop Backend
if [ -f "$SCRIPT_DIR/.backend.pid" ]; then
    BACKEND_PID=$(cat "$SCRIPT_DIR/.backend.pid")
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo "Stopping Backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        rm "$SCRIPT_DIR/.backend.pid"
    else
        echo "Backend process not running"
        rm "$SCRIPT_DIR/.backend.pid"
    fi
else
    echo "No backend PID file found"
fi

# Stop Frontend
if [ -f "$SCRIPT_DIR/.frontend.pid" ]; then
    FRONTEND_PID=$(cat "$SCRIPT_DIR/.frontend.pid")
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo "Stopping Frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
        rm "$SCRIPT_DIR/.frontend.pid"
    else
        echo "Frontend process not running"
        rm "$SCRIPT_DIR/.frontend.pid"
    fi
else
    echo "No frontend PID file found"
fi

echo ""
echo "✅ Services stopped"
echo ""
echo "Note: PostgreSQL is still running. To stop it:"
echo "  PGDATA=\${PGDATA:-\$HOME/postgres_data} pg_ctl -D \"\$PGDATA\" stop"
