Set WshShell = CreateObject("WScript.Shell")
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strPath

' 1. Determine Python executable
Dim pyExe
pyExe = strPath & "\venv\Scripts\python.exe"
Set fso = CreateObject("Scripting.FileSystemObject")
If Not fso.FileExists(pyExe) Then
    pyExe = "D:\Prog\ArchiveMasterFinal\venv\Scripts\python.exe"
End If
If Not fso.FileExists(pyExe) Then
    pyExe = "C:\Users\AD_4_\AppData\Local\Programs\Python\Python311\python.exe"
End If
If Not fso.FileExists(pyExe) Then
    pyExe = "python.exe"
End If

' 2. Launch Web Portal (Port 8000) Silently in background
WshShell.Run """" & pyExe & """ -m uvicorn elantony.web.api:app --host 0.0.0.0 --port 8000", 0, False

' 3. Short wait for server socket initialization
WScript.Sleep 2500

' 4. Launch Permanent Assistant Daemon (Telegram Bot + Tunnel + Library Watcher) Silently
WshShell.Run """" & pyExe & """ services\permanent_assistant\daemon.py", 0, False

Set WshShell = Nothing
Set fso = Nothing
