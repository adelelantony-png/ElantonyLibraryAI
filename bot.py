# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Cloud Bot Entrypoint
Runs the Telegram Bot Engine directly from project root.
"""
import sys
import os
import asyncio
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure UTF-8 output
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

if __name__ == "__main__":
    from scripts.run_bot import main
    asyncio.run(main())
