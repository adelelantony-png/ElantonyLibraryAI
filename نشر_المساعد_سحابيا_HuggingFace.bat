@echo off
chcp 65001 > nul
title ELANTONY LIBRARY AI - Hugging Face Cloud Deployer
cd /d "%~dp0"
cls
echo =====================================================================
echo   ✠ ELANTONY LIBRARY AI - نشر المساعد الذكي سحابياً 24/7 مجاناً ✠
echo =====================================================================
echo.
echo  هذا المشغل سينقل المنظومة كاملة لتعمل في سحابة Hugging Face مجاناً
echo  دون الحاجة لإبقاء جهازك الشخصي قيد التشغيل.
echo.

set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=D:\Prog\ArchiveMasterFinal\venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

"%PYTHON_EXE%" scripts\deploy_to_huggingface.py

if errorlevel 1 (
    echo.
    echo [تنبيه] حدث خطأ أثناء النشر.
)
pause
