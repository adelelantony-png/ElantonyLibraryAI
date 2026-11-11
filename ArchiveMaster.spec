# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect PyQt5 data files (plugins, styles, translations)
pyqt5_datas = collect_data_files('PyQt5')

datas = [
    ('app_icon.png', '.'),
] + pyqt5_datas

hiddenimports = [
    'PyQt5',
    'PyQt5.sip',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.QtPrintSupport',
    'fitz',
    'docx',
    'sqlite3',
    'requests',
    'bs4',
    'openpyxl',
    'concurrent.futures',
    'modules',
    'modules.ui_manager',
    'modules.database_handler',
    'modules.portable_config',
    'modules.themes',
    'modules.omnibox_dialog',
    'modules.in_app_reader',
    'modules.apologetics_hub_dialog',
    'modules.library_organizer',
    'modules.church_ocr_engine',
    'modules.ai_handler',
    'modules.topic_archive',
]

excludes = [
    'modules.church_drama_studio',
    'modules.sunday_school_dialog',
    'modules.sunday_school_builder',
    'modules.pastoral_care_journal',
    'modules.deeptutor_engine',
    'tkinter',
    'unittest',
    'test',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ArchiveMaster',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.png',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ArchiveMaster',
)
