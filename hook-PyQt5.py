# hook-PyQt5.py
from PyInstaller.utils.hooks import get_hook_dirs

# Add the path to the PyQt5 hooks that come with PyInstaller
__hooks_dir__ = get_hook_dirs('PyQt5')