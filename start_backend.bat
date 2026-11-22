@echo off
title CoursePilot - Backend Server
echo ===================================================
echo           Starting CoursePilot API Server
echo ===================================================
echo.
cd /d "%~dp0backend"
venv\Scripts\uvicorn.exe main:app --host 127.0.0.1 --port 8000 --reload
pause
