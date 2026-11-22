@echo off
title CoursePilot Server Launcher
echo ===================================================
echo        Starting CoursePilot AI Server + Tunnel
echo ===================================================
echo.

echo 1. Starting Cloudflare Public Tunnel (Syncs to Cloud)...
start "CoursePilot Cloudflare Tunnel" cmd /c "%~dp0start_tunnel.bat"

echo 2. Starting CoursePilot GPU Backend Server (Port 8000)...
echo.
cd /d "%~dp0backend"
venv\Scripts\uvicorn.exe main:app --host 127.0.0.1 --port 8000
pause
