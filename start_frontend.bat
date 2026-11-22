@echo off
title CoursePilot - Frontend UI
echo ===================================================
echo           Starting CoursePilot Web UI
echo ===================================================
echo.
cd /d "%~dp0frontend"
npm run dev
pause
