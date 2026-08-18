#!/usr/bin/env bash
# Render build script — runs on every deploy.
set -e

echo "==> Installing Python dependencies"
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Collecting static files"
python manage.py collectstatic --no-input

echo "==> Running database migrations"
python manage.py migrate --no-input

echo "==> Build complete"
