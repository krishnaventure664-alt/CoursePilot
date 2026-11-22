@echo off
title CoursePilot - Ngrok One-Time Setup
echo ========================================================
echo       CoursePilot - One-Time Permanent Tunnel Setup
echo ========================================================
echo.
echo 1. Open https://dashboard.ngrok.com in your browser (Sign in with Google).
echo 2. Go to 'Your Authtoken' on the left menu and copy your token.
echo 3. Go to 'Cloud Edge' -^> 'Domains' and click 'Claim Free Domain'.
echo.
set /p TOKEN="Paste your Ngrok Authtoken here: "
if "%TOKEN%"=="" (
    echo Error: Token cannot be empty.
    pause
    exit /b
)
"%~dp0ngrok.exe" config add-authtoken %TOKEN%

echo.
set /p DOMAIN="Paste your Free Static Domain (e.g. krishna-coursepilot.ngrok-free.app): "
if "%DOMAIN%"=="" (
    echo Error: Domain cannot be empty.
    pause
    exit /b
)

(
echo @echo off
echo title CoursePilot - Live Permanent Tunnel
echo echo ===================================================
echo echo      Starting CoursePilot Permanent Tunnel
echo echo      Domain: https://%DOMAIN%
echo echo ===================================================
echo echo.
echo echo Forwarding http://127.0.0.1:8000 to https://%DOMAIN%...
echo echo Keep this window OPEN while CoursePilot is in use.
echo echo.
echo "%%~dp0ngrok.exe" http --domain=%DOMAIN% 8000
echo pause
) > "%~dp0start_ngrok_tunnel.bat"

echo.
echo ========================================================
echo SUCCESS! Your permanent tunnel is created!
echo.
echo NEXT STEP:
echo Go to Vercel -^> CoursePilot -^> Settings -^> Environment Variables
echo Update NEXT_PUBLIC_API_URL to:
echo https://%DOMAIN%
echo.
echo From now on, simply double-click start_ngrok_tunnel.bat!
echo Your URL will NEVER change again.
echo ========================================================
pause
