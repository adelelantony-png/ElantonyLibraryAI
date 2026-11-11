@echo off
chcp 65001 >nul
cd /d "%~dp0"
title ArchiveMaster - Standalone EXE Builder

echo ========================================================
echo   [+] ArchiveMaster - Standalone EXE Builder
echo ========================================================
echo.

echo [1/3] فحص البيئة الافتراضية (Virtual Environment)...
set "PYTHON_EXE="
if exist "%~dp0venv\Scripts\python.exe" set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
if not defined PYTHON_EXE if exist "D:\Prog\ArchiveMasterFinal\venv\Scripts\python.exe" set "PYTHON_EXE=D:\Prog\ArchiveMasterFinal\venv\Scripts\python.exe"
if not defined PYTHON_EXE set "PYTHON_EXE=python"

echo مسار بايثون: %PYTHON_EXE%

echo [2/3] فحص أدوات التجميع ومكتبة PyInstaller...
"%PYTHON_EXE%" -m PyInstaller --version
if errorlevel 1 (
    echo [خطأ] PyInstaller غير مثبت. جاري التثبيت...
    "%PYTHON_EXE%" -m pip install pyinstaller
)

echo.
echo [3/3] جاري بناء النسخة التنفيذية (ArchiveMaster.exe)...
"%PYTHON_EXE%" -m PyInstaller --clean -y ArchiveMaster.spec

echo.
if exist "dist\ArchiveMaster\ArchiveMaster.exe" (
    echo ========================================================
    echo   [نجاح] تم بناء ملف التشغيل بنجاح!
    echo   المسار: dist\ArchiveMaster\ArchiveMaster.exe
    echo ========================================================
) else (
    echo [تنبيه] يرجى مراجعة سجل الأخطاء أعلاه.
)

pause
