@echo off
echo.
echo ====================================
echo   Fyers Token Generator UI Launcher
echo ====================================
echo.
echo Opening token generator interface...
echo.

REM Check if Chrome is available
where chrome >nul 2>nul
if %errorlevel%==0 (
    echo Using Chrome browser...
    start chrome "file://%~dp0token-generator-ui.html"
) else (
    REM Try Edge
    where msedge >nul 2>nul
    if %errorlevel%==0 (
        echo Using Edge browser...
        start msedge "file://%~dp0token-generator-ui.html"
    ) else (
        REM Fallback to default browser
        echo Using default browser...
        start "file://%~dp0token-generator-ui.html"
    )
)

echo.
echo Token Generator UI opened in your browser!
echo.
echo Quick Start:
echo 1. Enter your Fyers Client ID and App Secret
echo 2. Click 'Generate Login URL' and open Fyers login
echo 3. After login, paste the redirect URL to generate tokens
echo 4. Download AWS CLI commands to update your pipeline
echo.
echo Your credentials will be saved in the browser for next time.
echo.
pause
