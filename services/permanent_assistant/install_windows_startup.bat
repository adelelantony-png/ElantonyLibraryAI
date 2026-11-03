@echo off
chcp 65001 > nul
title تثبيت المساعد الدائم في بدء التشغيل
color 0A

echo =================================================================
echo  تثبيت ELANTONY LIBRARY AI ليعمل تلقائيا مع بدء تشغيل الويندوز
echo =================================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$WshShell = New-Object -ComObject WScript.Shell; $StartupFolder = [System.Environment]::GetFolderPath('Startup'); $Shortcut = $WshShell.CreateShortcut((Join-Path $StartupFolder 'ElantonyPermanentAssistant.lnk')); $Shortcut.TargetPath = 'wscript.exe'; $Shortcut.Arguments = '"D:\Prog\ArchiveMasterFinal\services\permanent_assistant\start_silent.vbs"'; $Shortcut.WorkingDirectory = 'D:\Prog\ArchiveMasterFinal\services\permanent_assistant'; $Shortcut.Description = 'ELANTONY LIBRARY AI - Permanent Assistant'; $Shortcut.Save()" > nul 2>&1

set "SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ElantonyPermanentAssistant.lnk"

if exist "%SHORTCUT%" goto :success
goto :failed

:success
echo  [OK] تم التثبيت والتسجيل بنجاح تام!
echo.
echo  المساعد مسجل الان في مجلد بدء التشغيل Startup Folder.
echo  سيبدا العمل دائما وبشكل صامت في الخلفية كلما فتحت الجهاز.
goto :end

:failed
echo  [!] حدث خطا اثناء انشاء اختصار بدء التشغيل.
goto :end

:end
echo.
echo =================================================================
pause
