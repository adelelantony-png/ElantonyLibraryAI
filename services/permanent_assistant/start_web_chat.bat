@echo off
chcp 65001 > nul
title ✠ ELANTONY LIBRARY AI - Web Chat Interface
color 0B

echo =================================================================
echo  ✠ ELANTONY LIBRARY AI - تشغيل واجهة الشات الذكي (مثل ChatGPT) ✠
echo =================================================================
echo.
echo  الواجهة متاحة مجاناً على جهازك بالرابط:
echo  http://localhost:8000
echo.
echo  جاري فتح المتصفح وتشغيل الخادم...
echo =================================================================

cd /d "D:\Prog\ArchiveMasterFinal"
set PYTHONPATH=D:\Prog\ArchiveMasterFinal

start http://localhost:8000

"D:\Prog\ArchiveMasterFinal\venv\Scripts\python.exe" -m uvicorn elantony.web.api:app --host 0.0.0.0 --port 8000

pause
