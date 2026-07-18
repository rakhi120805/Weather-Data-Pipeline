#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

echo "Checking database connection..."

# Use an inline python script to check if the PostgreSQL container is listening on port 5432.
# This prevents installing separate packages like netcat (nc) in our slim image.
python -c "
import socket
import time
import sys
import os

db_host = os.getenv('DB_HOST', 'db')
db_port = int(os.getenv('DB_PORT', '5432'))

print(f'Checking socket port availability on {db_host}:{db_port}...')
for i in range(30):
    try:
        with socket.create_connection((db_host, db_port), timeout=2):
            print('Connection established successfully!')
            sys.exit(0)
    except (socket.timeout, ConnectionRefusedError) as e:
        print(f'Database not ready yet... (Attempt {i+1}/30)')
        time.sleep(2)
print('Database failed to become ready within timeout.')
sys.exit(1)
"

echo "Database is online. Starting Weather ETL Pipeline run..."
exec python -m src.pipeline
