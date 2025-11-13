#!/bin/bash
set -e  # Exit on error

echo "Creating database..."
python create_database.py

echo "Starting application..."
exec python run.py