@echo off
chcp 65001 > nul
title تثبيت المساعد الدائم للعمل التلقائي مع الويندوز
color 0A

echo =================================================================
echo  ✠ تثبيت ELANTONY LIBRARY AI ليعمل تلقائياً في الخلفية ✠
echo =================================================================
echo.
echo سيتم تسجيل مهمة تشغيل تلقائية في Windows Task Scheduler ليعمل
echo المساعد دائماً وبشكل صامت في الخلفية بمجرد تشغيل الجهاز.
echo.

set "TASK_NAME=ElantonyPermanentAssistant"
set "VBS_SCRIPT=D:\Prog\ArchiveMasterFinal\services\permanent_assistant\start_silent.vbs"

schtasks /create /tn "%TASK_NAME%" /tr "wscript.exe \"%VBS_SCRIPT%\"" /sc onlogon /rl highest /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =================================================================
    echo  ✓ تم التثبيت والتسجيل بنجاح!
    echo  المساعد سيبدأ الآن العمل دائماً وتلقائياً مع كل فتح للويندوز.
    echo =================================================================
) else (
    echo.
    echo  ⚠️ فشل التسجيل التلقائي. يرجى إعادة التشغيل بصلاحية مسؤول (Run as Administrator).
)

echo.
pause
