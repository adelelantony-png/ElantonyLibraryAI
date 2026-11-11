@echo off
chcp 65001 >nul
cd /d "%~dp0"
title ArchiveMaster Standalone EXE

set "EXE_PATH="
if exist "%~dp0dist\ArchiveMaster\ArchiveMaster.exe" set "EXE_PATH=%~dp0dist\ArchiveMaster\ArchiveMaster.exe"
if not defined EXE_PATH if exist "D:\Prog\ArchiveMasterFinal\dist\ArchiveMaster\ArchiveMaster.exe" set "EXE_PATH=D:\Prog\ArchiveMasterFinal\dist\ArchiveMaster\ArchiveMaster.exe"
if not defined EXE_PATH if exist "%~dp0ArchiveMaster.exe" set "EXE_PATH=%~dp0ArchiveMaster.exe"

if not defined EXE_PATH goto :NOT_FOUND

echo =========================================================================
echo  [+] تشغيل النسخة التنفيذية المستقلة: ArchiveMaster.exe
echo =========================================================================
echo المسار: %EXE_PATH%
echo.
start "" "%EXE_PATH%"
exit /b 0

:NOT_FOUND
echo [خطأ] لم يتم العثور على ملف ArchiveMaster.exe!
echo يمكنك بناء النسخة أولا عبر تشغيل Build_Standalone_EXE.bat
pause
exit /b 1
