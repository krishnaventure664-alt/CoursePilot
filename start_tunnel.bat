@echo off
title CoursePilot - Live Cloudflare Tunnel
cd /d "%~dp0"
backend\venv\Scripts\python.exe backend\tunnel_runner.py
pause
