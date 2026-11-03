@echo off
chcp 65001 > nul
title ELANTONY LIBRARY AI - Permanent Assistant
color 0B

echo =================================================================
echo  ✠ ELANTONY LIBRARY AI - تشغيل المساعد الدائم المستقل ✠
echo =================================================================
echo.

set "PYTHON_EXE=D:\Prog\ArchiveMasterFinal\venv\Scripts\python.exe"
set "DAEMON_PY=D:\Prog\ArchiveMasterFinal\services\permanent_assistant\daemon.py"

"%PYTHON_EXE%" "%DAEMON_PY%"

pause
