@echo off
echo 🚨 EMERGENCY DJANGO SERVER STARTER
echo =====================================

cd /d "c:\Users\ADMIN\Desktop\school sasa report\backend"

echo.
echo 🔍 Checking Python and Django...
python --version
python -c "import django; print('Django version:', django.get_version())"

echo.
echo 🧹 Clearing any cached files...
if exist "db.sqlite3-journal" del "db.sqlite3-journal"
if exist "__pycache__" rmdir /s /q "__pycache__"

echo.
echo 🔧 Running migrations...
python manage.py migrate --run-syncdb

echo.
echo 👥 Creating test users...
python create_test_users.py

echo.
echo 🚀 Starting Django server on 127.0.0.1:8000...
echo    If this fails, try manually: python manage.py runserver 127.0.0.1:8001
echo    Press Ctrl+C to stop the server
echo.

python manage.py runserver 127.0.0.1:8000 --verbosity=2

pause