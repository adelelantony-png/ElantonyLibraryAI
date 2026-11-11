@echo off
chcp 65001 >nul
echo ========================================================
echo   ✠ ArchiveMaster - Standalone EXE Builder ✠
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/3] تفعيل البيئة الافتراضية (Virtual Environment)...
if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

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
