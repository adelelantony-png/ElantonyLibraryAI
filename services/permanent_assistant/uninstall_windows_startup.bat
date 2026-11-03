@echo off
chcp 65001 > nul
title إلغاء التشغيل التلقائي للمساعد الدائم
color 0C

echo =================================================================
echo  إلغاء مهمة التشغيل التلقائي لمساعد ELANTONY LIBRARY AI
echo =================================================================
echo.

set "TASK_NAME=ElantonyPermanentAssistant"
schtasks /delete /tn "%TASK_NAME%" /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ تم إلغاء مهمة التشغيل التلقائي بنجاح.
) else (
    echo.
    echo ⚠️ لم يتم العثور على المهمة أو تم إلغاؤها مسبقاً.
)

echo.
pause
