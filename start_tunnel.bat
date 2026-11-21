@echo off
title CoursePilot - Live Cloudflare Tunnel
echo ===================================================
echo     Starting CoursePilot Public Cloudflare Tunnel
echo ===================================================
echo.
echo Forwarding http://127.0.0.1:8000 to Cloudflare's Global Network...
echo Keep this window OPEN while you or other users are using CoursePilot.
echo.
cloudflared.exe tunnel --url http://127.0.0.1:8000
pause
