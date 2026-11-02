@echo off
title ELANTONY LIBRARY AI - Disable Windows Autostart
chcp 65001 > nul
cd /d "%~dp0"

echo =========================================================================
echo  ✠ إلغاء التشغيل التلقائي لبوت المكتبة الكنسية مع بدء تشغيل الويندوز ✠
echo =========================================================================
echo.

powershell -NoProfile -Command "$lnk = [System.IO.Path]::Combine($env:APPDATA, 'Microsoft\Windows\Start Menu\Programs\Startup', 'ElantonyLibraryBot.lnk'); if (Test-Path $lnk) { Remove-Item $lnk -Force; Write-Host ' [✓] تم إلغاء التشغيل التلقائي بنجاح.' -ForegroundColor Yellow } else { Write-Host ' [i] لم يكن التشغيل التلقائي مفعلاً مسبقاً.' -ForegroundColor Cyan }"

echo.
echo =========================================================================
pause
