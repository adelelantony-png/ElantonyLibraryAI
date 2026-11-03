@echo off
chcp 65001 > nul
title ELANTONY LIBRARY AI - Remote Cloud Access Launcher
cd /d "%~dp0"
cls
echo =====================================================================
echo   ✠ ELANTONY LIBRARY AI - مشغل الوصول السحابي عن بُعد للمساعد ✠
echo =====================================================================
echo.
echo  جاري إنشاء الرابط العالمي الآمن (HTTPS)...
echo.

set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=D:\Prog\ArchiveMasterFinal\venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

"%PYTHON_EXE%" scripts\run_remote_tunnel.py

if errorlevel 1 (
    echo.
    echo [تنبيه] حدث خطأ أو توقف النفق.
    pause
)
