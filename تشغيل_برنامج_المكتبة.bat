@echo off
chcp 65001 >nul
cd /d "%~dp0"
title ArchiveMaster Final - Coptic Library

set "PYTHON_EXE="
if exist "%~dp0venv\Scripts\python.exe" set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
if not defined PYTHON_EXE if exist "D:\Prog\ArchiveMasterFinal\venv\Scripts\python.exe" set "PYTHON_EXE=D:\Prog\ArchiveMasterFinal\venv\Scripts\python.exe"
if not defined PYTHON_EXE if exist "C:\Users\AD_4_\AppData\Local\Programs\Python\Python311\python.exe" set "PYTHON_EXE=C:\Users\AD_4_\AppData\Local\Programs\Python\Python311\python.exe"
if not defined PYTHON_EXE set "PYTHON_EXE=python"

echo =========================================================================
echo  [+] جاري تشغيل برنامج ArchiveMaster - مكتبة الصليب القبطية الأرثوذكسية
echo =========================================================================
echo مسار بايثون: %PYTHON_EXE%
echo.

"%PYTHON_EXE%" main.py

if errorlevel 1 goto :ERROR
exit /b 0

:ERROR
echo.
echo [تنبيه] تم إيقاف التطبيق أو حدث خطأ أثناء التشغيل.
pause
exit /b 1
