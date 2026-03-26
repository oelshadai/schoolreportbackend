#!/usr/bin/env bash
# Render build script for backend
set -o errexit

# Install wkhtmltopdf for PDF generation
apt-get update && apt-get install -y wkhtmltopdf || true

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
