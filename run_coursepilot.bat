@echo off
title CoursePilot Launcher
echo ===================================================
echo           Launching CoursePilot (Local)
echo ===================================================
echo.

echo 1. Starting Backend API Server (port 8000)...
start "CoursePilot Backend" cmd /c "%~dp0start_backend.bat"

timeout /t 3 /nobreak >nul

echo 2. Starting Frontend Web UI (port 3000)...
start "CoursePilot Frontend" cmd /c "%~dp0start_frontend.bat"

timeout /t 5 /nobreak >nul

echo 3. Opening CoursePilot in your browser...
start http://localhost:3000

echo.
echo ===================================================
echo CoursePilot is now running!
echo Keep the backend and frontend terminal windows open.
echo ===================================================
