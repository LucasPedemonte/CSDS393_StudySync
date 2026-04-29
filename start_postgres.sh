#!/bin/bash
# Start PostgreSQL for StudySync on Markov

set -e

module load PostgreSQL/16.1-GCCcore-13.2.0

PGDATA="${PGDATA:-$HOME/postgres_data}"

if [ ! -d "$PGDATA" ]; then
    echo "Initializing PostgreSQL data directory at $PGDATA"
    initdb -D "$PGDATA"
fi

rm -f "$PGDATA/postmaster.pid"
pg_ctl -D "$PGDATA" -l "$PGDATA/logfile" start

if ! psql -lqt | cut -d \| -f 1 | grep -qw studysync_db; then
    createdb studysync_db
fi

echo "PostgreSQL started on $(hostname)"
echo "Data directory: $PGDATA"
echo "Database: studysync_db"
echo "Socket: /tmp/.s.PGSQL.5432"
