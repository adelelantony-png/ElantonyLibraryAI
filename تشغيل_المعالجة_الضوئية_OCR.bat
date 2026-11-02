@echo off
title ELANTONY OCR Engine - Background Worker
chcp 65001 >nul
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=D:\Prog\ArchiveMasterFinal\venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=C:\Users\AD_4_\AppData\Local\Programs\Python\Python311\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

echo =========================================================================
echo  ✠ مشغل القراءة الضوئية واستخراج نصوص الكتب المصورة في الخلفية (OCR) ✠
echo =========================================================================
echo  [*] يعمل بأولوية معالج منخفضة جداً حتى لا يؤثر على سرعة جهازك إطلاقاً.
echo  [*] يمكنك إيقافه أو إغلاقه في أي وقت، وسيستأنف المعالجة من حيث توقف تلقائياً.
echo =========================================================================
echo.

"%PYTHON_EXE%" scripts\run_background_ocr.py

if errorlevel 1 (
    echo.
    echo [تنبيه] توقف مشغل الـ OCR.
    pause
)
