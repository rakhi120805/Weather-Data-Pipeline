#!/bin/sh
set -e

# If PostgreSQL is explicitly configured and not sqlite/default
if [ "$DB_TYPE" = "postgresql" ] && [ -n "$DB_HOST" ]; then
    echo "Checking database connection on $DB_HOST:${DB_PORT:-5432}..."
    python -c "
import socket
import time
import sys
import os

db_host = os.getenv('DB_HOST', 'localhost')
db_port = int(os.getenv('DB_PORT', '5432'))

for i in range(30):
    try:
        with socket.create_connection((db_host, db_port), timeout=2):
            print('Connection established successfully!')
            sys.exit(0)
    except (socket.timeout, ConnectionRefusedError, socket.gaierror):
        print(f'Database not ready yet... (Attempt {i+1}/30)')
        time.sleep(2)
print('Database check completed or timed out.')
"
fi

# Run an initial pipeline population run
echo "Running initial ETL check..."
python -m src.pipeline || true

# Start web service listening on $PORT
PORT="${PORT:-8000}"
echo "Starting Weather Data Pipeline FastAPI Web Server on port $PORT..."
exec uvicorn main:app --host 0.0.0.0 --port "$PORT"
