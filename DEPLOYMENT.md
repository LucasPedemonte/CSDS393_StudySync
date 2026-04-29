# StudySync Deployment Guide for Markov

## Prerequisites

Run StudySync from a Markov compute node, not the login node.

Load the required modules first:

```bash
module load PostgreSQL/16.1-GCCcore-13.2.0
module load nodejs/20.9.0-GCCcore-13.2.0
```

## One-time setup

### Backend

```bash
cd /home/lap127/StudySyncGit/CSDS393_StudySync/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set:

```env
DATABASE_URL=postgresql:///studysync_db?host=/tmp
```

### Frontend

```bash
cd /home/lap127/StudySyncGit/CSDS393_StudySync/frontend
npm install
cp .env.example .env
```

Set:

```env
REACT_APP_API_BASE_URL=https://ondemand-markov.case.edu/rnode/<your-compute-node>/8000
```

The rest of the Firebase values can stay the same as `frontend/.env.example`.

## Start services

### Option 1: helper scripts

```bash
cd /home/lap127/StudySyncGit/CSDS393_StudySync
./start_postgres.sh
./start_services.sh
```

### Option 2: manual startup

Start PostgreSQL:

```bash
cd /home/lap127/StudySyncGit/CSDS393_StudySync
./start_postgres.sh
```

Start the backend:

```bash
cd /home/lap127/StudySyncGit/CSDS393_StudySync/backend
source .venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Start the frontend:

```bash
cd /home/lap127/StudySyncGit/CSDS393_StudySync/frontend
npm run build
npx serve -s build -l 3000
```

## Access URLs

Replace `$(hostname)` with your active compute node name if you are typing the URL manually.

- Frontend: `https://ondemand-markov.case.edu/rnode/$(hostname)/3000/`
- Backend docs: `https://ondemand-markov.case.edu/rnode/$(hostname)/8000/docs`

`start_services.sh` prints the exact URLs automatically.

## Stop services

Stop backend and frontend:

```bash
cd /home/lap127/StudySyncGit/CSDS393_StudySync
./stop_services.sh
```

Stop PostgreSQL:

```bash
module load PostgreSQL/16.1-GCCcore-13.2.0
PGDATA="${PGDATA:-$HOME/postgres_data}" pg_ctl -D "$PGDATA" stop
```

## Troubleshooting

- If `npm` is not found, reload the Node module with `module load nodejs/20.9.0-GCCcore-13.2.0`.
- If PostgreSQL fails to start, remove a stale PID file with `rm -f ~/postgres_data/postmaster.pid` and rerun `./start_postgres.sh`.
- If the frontend cannot reach the backend, confirm `frontend/.env` points to the correct `rnode/<hostname>/8000` URL.
- If backend tests fail during collection, reinstall requirements so `hypothesis` is present.
