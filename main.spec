# -*- mode: python ; coding: utf-8 -*-

import os
import sys
# استيراد الأداة الرسمية من PyInstaller للعثور على ملفات البيانات الخاصة بالمكتبات
from PyInstaller.utils.hooks import collect_data_files

# --- Block Cipher (standard) ---
block_cipher = None


# --- Analysis Section ---
a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    
    # 'datas' لتضمين الملفات غير البرمجية.
    # نستخدم الدالة الرسمية collect_data_files('PyQt5') التي تجلب كل ما تحتاجه المكتبة
    # من ملفات إضافية (plugins) وملفات DLL بشكل تلقائي ومضمون.
    datas=[('app_icon.png', '.')] + collect_data_files('PyQt5'),
    
    # 'hiddenimports' لإعلام PyInstaller بالمكتبات التي قد لا يجدها.
    hiddenimports=[
        'PyQt5.sip',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtPrintSupport',
        'fitz',
        'concurrent.futures',
        'deep_translator'  # -- تمت إضافة هذه المكتبة هنا --
    ],
    
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

# --- PYZ, EXE, COLLECT Sections (standard) ---
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
    icon='app_icon.png'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ArchiveMaster'
)