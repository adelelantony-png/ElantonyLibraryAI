@echo off
title ArchiveMaster Final - Coptic Library
chcp 65001 >nul
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=D:\Prog\ArchiveMasterFinal\venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=C:\Users\AD_4_\AppData\Local\Programs\Python\Python311\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

echo =========================================================================
echo  ✠ جاري تشغيل برنامج ArchiveMaster - مكتبة الصليب القبطية الأرثوذكسية ✠
echo =========================================================================
"%PYTHON_EXE%" main.py

if errorlevel 1 (
    echo.
    echo [تنبيه] تم إيقاف التطبيق أو حدث خطأ أثناء التشغيل.
    pause
)
