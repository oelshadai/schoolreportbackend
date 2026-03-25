@echo off
echo ========================================
echo ReportLab PDF Generation Test Suite
echo ========================================
echo.

cd /d "%~dp0"

echo Step 1: Setting up ReportLab...
python setup_reportlab.py
if %errorlevel% neq 0 (
    echo.
    echo ERROR: ReportLab setup failed!
    echo Please check the output above for details.
    pause
    exit /b 1
)

echo.
echo Step 2: Running comprehensive tests...
python test_reportlab_pdf.py
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Some tests failed!
    echo Please check the output above for details.
    pause
    exit /b 1
)

echo.
echo ========================================
echo All tests completed successfully!
echo ========================================
echo.
echo ReportLab PDF generation is working correctly.
echo You can now generate PDF reports in your Django application.
echo.
echo Generated test files:
echo - reportlab_test.pdf (basic ReportLab test)
echo - test_report.pdf (full report template test)
echo.
pause