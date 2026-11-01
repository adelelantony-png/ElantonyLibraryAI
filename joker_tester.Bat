@echo off
setlocal

:: 1. Get file path from drag-and-drop
set "PY_FILE=%~1"

:: 2. If no file was dragged, open File Explorer dialog
if "%PY_FILE%"=="" (
    echo Opening file selection dialog...
    for /f "delims=" %%I in ('powershell -NoProfile -Command "Add-Type -AssemblyName System.windows.forms; $f = New-Object System.Windows.Forms.OpenFileDialog; $f.Filter = 'Python Files (*.py)^|*.py'; $f.Title = 'Select a Python file to run'; if ($f.ShowDialog() -eq 'OK') { $f.FileName }"') do set "PY_FILE=%%I"
)

:: Check if the user closed the dialog without selecting a file
if "%PY_FILE%"=="" (
    echo No file selected. The program will now exit...
    pause
    exit /b
)

echo Selected file: "%PY_FILE%"
echo ----------------------------------------
echo Scanning and installing required dependencies (if any)...

:: 3. Create a smart temporary Python script
set "TEMP_PY=%temp%\smart_dep_installer.py"

echo import sys, subprocess, ast, importlib.util, datetime, os > "%TEMP_PY%"
echo file_path = r"%PY_FILE%" >> "%TEMP_PY%"
echo script_dir = os.path.dirname(file_path) >> "%TEMP_PY%"
echo log_file = os.path.join(script_dir, "log.txt") >> "%TEMP_PY%"
echo log_entries = ["\n=== Execution: " + str(datetime.datetime.now()) + " ===", f"Target File: {file_path}"] >> "%TEMP_PY%"
echo req_file = os.path.join(script_dir, "requirements.txt") >> "%TEMP_PY%"
echo if os.path.exists(req_file): >> "%TEMP_PY%"
echo     log_entries.append("[INFO] requirements.txt found. Installing from it...") >> "%TEMP_PY%"
echo     print("Found requirements.txt. Installing dependencies...") >> "%TEMP_PY%"
echo     res = subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_file], capture_output=True, text=True) >> "%TEMP_PY%"
echo     if res.returncode == 0: >> "%TEMP_PY%"
echo         log_entries.append("[SUCCESS] requirements.txt installed.") >> "%TEMP_PY%"
echo     else: >> "%TEMP_PY%"
echo         log_entries.append(f"[FAILED] Error installing requirements.txt: {res.stderr.strip()}") >> "%TEMP_PY%"
echo else: >> "%TEMP_PY%"
echo     log_entries.append("[INFO] No requirements.txt found. Scanning imports...") >> "%TEMP_PY%"
echo     try: >> "%TEMP_PY%"
echo         with open(file_path, "r", encoding="utf-8") as f: tree = ast.parse(f.read()) >> "%TEMP_PY%"
echo         imports = set() >> "%TEMP_PY%"
echo         for node in ast.walk(tree): >> "%TEMP_PY%"
echo             if isinstance(node, ast.Import): >> "%TEMP_PY%"
echo                 for n in node.names: imports.add(n.name.split('.')[0]) >> "%TEMP_PY%"
echo             elif isinstance(node, ast.ImportFrom) and node.module: >> "%TEMP_PY%"
echo                 imports.add(node.module.split('.')[0]) >> "%TEMP_PY%"
echo         name_map = {'cv2': 'opencv-python', 'bs4': 'beautifulsoup4', 'PIL': 'Pillow', 'sklearn': 'scikit-learn', 'yaml': 'pyyaml', 'dotenv': 'python-dotenv', 'pptx': 'python-pptx', 'docx': 'python-docx', 'fitz': 'PyMuPDF'} >> "%TEMP_PY%"
echo         for mod in imports: >> "%TEMP_PY%"
echo             local_py = os.path.join(script_dir, mod + ".py") >> "%TEMP_PY%"
echo             local_dir = os.path.join(script_dir, mod) >> "%TEMP_PY%"
echo             if os.path.exists(local_py) or os.path.isdir(local_dir): >> "%TEMP_PY%"
echo                 log_entries.append(f"[INFO] '{mod}' is a local module. Skipping.") >> "%TEMP_PY%"
echo                 continue >> "%TEMP_PY%"
echo             try: spec = importlib.util.find_spec(mod) >> "%TEMP_PY%"
echo             except Exception: spec = None >> "%TEMP_PY%"
echo             if spec is not None: >> "%TEMP_PY%"
echo                 log_entries.append(f"[SUCCESS] Module '{mod}' is already installed.") >> "%TEMP_PY%"
echo             else: >> "%TEMP_PY%"
echo                 pip_name = name_map.get(mod, mod) >> "%TEMP_PY%"
echo                 print(f"Installing missing module: {pip_name} ...") >> "%TEMP_PY%"
echo                 res = subprocess.run([sys.executable, "-m", "pip", "install", pip_name], capture_output=True, text=True) >> "%TEMP_PY%"
echo                 if res.returncode == 0: log_entries.append(f"[SUCCESS] Installed missing module: {pip_name}") >> "%TEMP_PY%"
echo                 else: log_entries.append(f"[FAILED] Failed to install {pip_name}. Error: {res.stderr.strip()}") >> "%TEMP_PY%"
echo     except Exception as e: >> "%TEMP_PY%"
echo         log_entries.append(f"[CRITICAL ERROR] {str(e)}") >> "%TEMP_PY%"
echo with open(log_file, "a", encoding="utf-8") as log_f: log_f.write("\n".join(log_entries) + "\n") >> "%TEMP_PY%"

:: Run the dependency checker
python "%TEMP_PY%"
del "%TEMP_PY%"

echo ----------------------------------------
echo Running the main script...
echo ----------------------------------------

:: Extract the directory of the target file and change to it
for %%I in ("%PY_FILE%") do cd /d "%%~dpI"

python "%PY_FILE%"

echo ----------------------------------------
echo Execution finished.
pause