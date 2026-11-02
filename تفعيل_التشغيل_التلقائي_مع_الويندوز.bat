@echo off
title ELANTONY LIBRARY AI - Enable Windows Autostart
chcp 65001 > nul
cd /d "%~dp0"

echo =========================================================================
echo  ✠ تفعيل التشغيل التلقائي لبوت المكتبة الكنسية مع بدء تشغيل الويندوز ✠
echo =========================================================================
echo.

set "VBS_PATH=%~dp0تشغيل_البوت_في_الخلفية_صامت.vbs"

powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.IO.Path]::Combine($env:APPDATA, 'Microsoft\Windows\Start Menu\Programs\Startup', 'ElantonyLibraryBot.lnk')); $s.TargetPath = '%VBS_PATH%'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'ELANTONY LIBRARY AI Telegram Bot 24/7'; $s.Save(); Write-Host ' [✓] تم تفعيل التشغيل التلقائي بنجاح! سيعمل البوت صامتاً في الخلفية بمجرد تشغيل الكمبيوتر.' -ForegroundColor Green"

echo.
echo =========================================================================
pause
