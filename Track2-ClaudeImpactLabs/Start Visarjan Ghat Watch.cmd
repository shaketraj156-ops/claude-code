@echo off
cd /d "%~dp0visarjan-demo"
python start_demo.py
if errorlevel 1 pause
