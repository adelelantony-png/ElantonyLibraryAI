@echo off
title ELANTONY LIBRARY AI - Enable Windows Autostart
chcp 65001 > nul
cd /d "%~dp0"

echo =========================================================================
echo  ✠ تفعيل التشغيل التلقائي لمنظومة المكتبة الكنسية الشاملة مع بدء الويندوز ✠
echo  (بوابة الويب على بورت 8000 + بوت تليجرام + نفق الوصول عن بعد الذكي)
echo =========================================================================
echo.

set "VBS_PATH=%~dp0تشغيل_المنظومة_الشاملة_صامت.vbs"

powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.IO.Path]::Combine($env:APPDATA, 'Microsoft\Windows\Start Menu\Programs\Startup', 'ElantonyLibraryCompleteSystem.lnk')); $s.TargetPath = '%VBS_PATH%'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'ELANTONY LIBRARY AI Complete System 24/7 (Web + Bot + Tunnel)'; $s.Save(); Write-Host ' [✓] تم تفعيل التشغيل التلقائي بنجاح! ستعمل منظومة المكتبة الشاملة (الويب والبوت والنفق) صامتة في الخلفية بمجرد تشغيل الكمبيوتر.' -ForegroundColor Green"

echo.
echo =========================================================================
pause
