@echo off
chcp 65001 > nul
title الغاء التشغيل التلقائي للمساعد الدائم
color 0C

echo =================================================================
echo  الغاء التشغيل التلقائي لمساعد ELANTONY LIBRARY AI
echo =================================================================
echo.

set "SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ElantonyPermanentAssistant.lnk"

if exist "%SHORTCUT%" goto :found
goto :notfound

:found
del "%SHORTCUT%" > nul 2>&1
echo  [OK] تم حذف اختصار بدء التشغيل بنجاح.
echo  لن يعمل المساعد تلقائيا عند فتح الجهاز بعد الان.
goto :end

:notfound
echo  [i] المساعد غير مسجل في بدء التشغيل حاليا.
goto :end

:end
echo.
echo =================================================================
pause
