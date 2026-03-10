@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_HTML=%SCRIPT_DIR%heap_usage_plot.html"

if "%~1"=="" (
    echo Drag and drop one or more CSV files onto this .bat file.
    echo.
    echo Example:
    echo   plot_heap_csv_dragdrop.bat test_log1.csv test_log2.csv
    pause
    exit /b 1
)

pushd "%SCRIPT_DIR%"
python "%SCRIPT_DIR%plot_heap_csv.py" %* -o "%OUTPUT_HTML%" --auto-open
set "EXIT_CODE=%ERRORLEVEL%"
popd

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Plot generation failed.
    pause
)

exit /b %EXIT_CODE%