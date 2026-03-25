@echo off
echo 🔍 DJANGO SERVER DIAGNOSTIC
echo ========================

cd /d "c:\Users\ADMIN\Desktop\school sasa report\backend"

echo.
echo 1. Checking Python and Django...
python --version
python -c "import django; print('Django version:', django.get_version())"

echo.
echo 2. Testing Django settings...
python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings'); import django; django.setup(); print('✅ Django setup OK')"

echo.
echo 3. Checking if port 8000 is in use...
netstat -an | findstr :8000

echo.
echo 4. Testing database connection...
python manage.py check --deploy

echo.
echo 5. Running migrations...
python manage.py migrate

echo.
echo 6. Creating test users...
python create_test_users.py

echo.
echo 7. Starting server with detailed output...
echo    If you see "Starting development server", the server is working
echo    Press Ctrl+C to stop
echo.

python manage.py runserver 127.0.0.1:8000 --verbosity=2

pause