@echo off
chcp 65001 > nul
title ELANTONY LIBRARY AI - Telegram Bot Launcher
cd /d "%~dp0"
cls
echo =====================================================================
echo   ✠ ELANTONY LIBRARY AI - تشغيل بوت المكتبة الكنسية الذكية ✠
echo =====================================================================
echo.
echo  جاري التحقق من البيئة وتشغيل البوت بالأزرار التفاعلية...
echo.

set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=D:\Prog\ArchiveMasterFinal\venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=C:\Users\AD_4_\AppData\Local\Programs\Python\Python311\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

"%PYTHON_EXE%" scripts\run_bot.py

if errorlevel 1 (
    echo.
    echo [تنبيه] توقف مشغل البوت.
    pause
)
