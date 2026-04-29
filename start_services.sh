#!/bin/bash
# Start backend and frontend on a Markov compute node

set -e  # Exit on error

echo "🚀 Starting StudySync Backend and Frontend..."
echo "=================================================="
echo ""

# Get the current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# ============================================================================
# LOAD MODULES
# ============================================================================
echo "📦 Loading required modules..."
module load PostgreSQL/16.1-GCCcore-13.2.0
echo "   ✓ PostgreSQL loaded"

module load nodejs/20.9.0-GCCcore-13.2.0
echo "   ✓ Node.js loaded"
node --version
npm --version
echo ""

# ============================================================================
# START POSTGRESQL
# ============================================================================
echo "🗄️  Checking PostgreSQL..."
if [ ! -S /tmp/.s.PGSQL.5432 ]; then
    echo "   Starting PostgreSQL..."
    rm -f ~/postgres_data/postmaster.pid
    pg_ctl -D ~/postgres_data -l ~/postgres_data/logfile start
    sleep 3
    echo "   ✓ PostgreSQL started"
else
    echo "   ✓ PostgreSQL already running"
fi

# Check if database exists, create if not
echo "   Checking database..."
if psql -lqt | cut -d \| -f 1 | grep -qw studysync_db; then
    echo "   ✓ Database 'studysync_db' exists"
else
    echo "   Creating database 'studysync_db'..."
    createdb studysync_db
    echo "   ✓ Database created"
fi
echo ""

# ============================================================================
# START BACKEND
# ============================================================================
echo "🔧 Starting Backend on port 8000..."
cd "$SCRIPT_DIR/backend"

if [ ! -d ".venv" ]; then
    echo "   ❌ Virtual environment not found!"
    exit 1
fi

echo "   Activating virtual environment..."
source .venv/bin/activate

echo "   Starting uvicorn server..."
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "   ✓ Backend started with PID: $BACKEND_PID"

# Wait and check if backend is running
sleep 2
if ps -p $BACKEND_PID > /dev/null; then
    echo "   ✓ Backend is running"
    echo "   📝 Viewing last 10 lines of backend.log:"
    tail -10 backend.log
else
    echo "   ❌ Backend failed to start! Check backend.log:"
    cat backend.log
    exit 1
fi
echo ""

# ============================================================================
# BUILD & START FRONTEND
# ============================================================================
echo "🎨 Starting Frontend on port 3000..."
cd "$SCRIPT_DIR/frontend"

# Check if build exists or needs rebuild
if [ ! -d "build" ]; then
    echo "   📦 Build directory not found. Building frontend..."
    npm run build
    echo "   ✓ Build complete"
else
    echo "   ✓ Build directory exists"
fi

echo "   Starting serve..."
nohup npx serve -s build -l 3000 > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   ✓ Frontend started with PID: $FRONTEND_PID"

# Wait and check if frontend is running
sleep 2
if ps -p $FRONTEND_PID > /dev/null; then
    echo "   ✓ Frontend is running"
    echo "   📝 Viewing last 10 lines of frontend.log:"
    tail -10 frontend.log
else
    echo "   ❌ Frontend failed to start! Check frontend.log:"
    cat frontend.log
    exit 1
fi
echo ""

# Save PIDs for easy shutdown
echo "$BACKEND_PID" > "$SCRIPT_DIR/.backend.pid"
echo "$FRONTEND_PID" > "$SCRIPT_DIR/.frontend.pid"

echo "=================================================="
echo "✅ All services started successfully!"
echo "=================================================="
echo ""
HOSTNAME_VALUE="$(hostname)"

echo "📍 Access your application:"
echo "   Frontend: https://ondemand-markov.case.edu/rnode/$HOSTNAME_VALUE/3000/"
echo "   Backend:  https://ondemand-markov.case.edu/rnode/$HOSTNAME_VALUE/8000/docs"
echo ""
echo "📝 Monitor logs:"
echo "   Backend:  tail -f $SCRIPT_DIR/backend/backend.log"
echo "   Frontend: tail -f $SCRIPT_DIR/frontend/frontend.log"
echo ""
echo "🛑 To stop services: ./stop_services.sh"
echo ""
