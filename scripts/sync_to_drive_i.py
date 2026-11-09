# -*- coding: utf-8 -*-
import shutil
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

source_dir = r"D:\Prog\ArchiveMasterFinal"
target_dir = r"I:\2021\2020\✠ Cross Coptic Library ✠\ArchiveMaster"

files_to_sync = [
    r"elantony\ai\gemini_provider.py",
    r"elantony\ai\rule_based_provider.py",
    r"elantony\classifier\source_classifier.py",
    r"elantony\search\search_engine.py",
    r"elantony\database\repository.py",
    r"elantony\services\docx_exporter.py",
    r"elantony\telegram\handlers.py",
    r"elantony\web\api.py",
    r"services\permanent_assistant\tunnel_watchdog.py",
    r"services\permanent_assistant\daemon.py"
]

for rel_p in files_to_sync:
    s = os.path.join(source_dir, rel_p)
    t = os.path.join(target_dir, rel_p)
    if os.path.exists(s):
        os.makedirs(os.path.dirname(t), exist_ok=True)
        shutil.copy2(s, t)
        print(f"Synced {rel_p} -> {t}")

print("Sync to Drive I completed successfully!")
