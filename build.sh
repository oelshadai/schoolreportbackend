#!/usr/bin/env bash
# Render build script for backend
set -o errexit

# Install wkhtmltopdf for PDF generation
apt-get update && apt-get install -y wkhtmltopdf || true

pip install -r requirements.txt

# Clean stale migration records that reference deleted migration files
python manage.py shell -c "
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute(\"DELETE FROM django_migrations WHERE app='assignments' AND name IN ('0002_add_missing_fields', '0003_add_question_fields')\")
        print(f'Cleaned {cursor.rowcount} stale migration records')
except Exception as e:
    print(f'Migration cleanup skipped: {e}')
" || true

python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Fix any students that are missing user accounts
python manage.py fix_student_users || true
