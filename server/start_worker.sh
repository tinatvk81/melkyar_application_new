#!/bin/sh
set -e
cd /app/server
pip install -r requirements.txt --no-cache-dir
python -m app.discovery.services.seed_neighborhoods
exec python -m app.discovery.jobs.scheduler