@echo off
title ArchiveMaster Final - Coptic Library
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=C:\Users\AD_4_\AppData\Local\Programs\Python\Python311\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

"%PYTHON_EXE%" main.py

if errorlevel 1 (
    echo.
    echo [Notice] Application stopped or encountered an error.
    pause
)
