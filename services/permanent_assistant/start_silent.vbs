' VBScript to launch ELANTONY Permanent Assistant invisibly in background (zero console window)
Set WshShell = CreateObject("WScript.Shell")
strPath = WshShell.CurrentDirectory

pythonExe = "D:\Prog\ArchiveMasterFinal\venv\Scripts\python.exe"
daemonPy  = "D:\Prog\ArchiveMasterFinal\services\permanent_assistant\daemon.py"

cmd = """" & pythonExe & """ """ & daemonPy & """"
WshShell.Run cmd, 0, False
Set WshShell = Nothing
