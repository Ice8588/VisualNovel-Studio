# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for VisualNovel Studio."""

import sys
from pathlib import Path

block_cipher = None
root = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(root)],
    binaries=[],
    datas=[
        # 播放引擎檔案
        (str(root / 'src' / 'engine' / 'index.html'), 'src/engine'),
        (str(root / 'src' / 'engine' / 'engine.js'), 'src/engine'),
        (str(root / 'src' / 'engine' / 'effects.js'), 'src/engine'),
        (str(root / 'src' / 'engine' / 'style.css'), 'src/engine'),
        (str(root / 'src' / 'engine' / 'script.json'), 'src/engine'),
        # 內嵌字型（Noto Sans TC）與設計資產
        (str(root / 'assets'), 'assets'),
    ],
    hiddenimports=[
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebEngineCore',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'pytest',
        'setuptools',
        'pip',
        'PyQt6.QtBluetooth',
        'PyQt6.QtDBus',
        'PyQt6.QtDesigner',
        'PyQt6.QtHelp',
        'PyQt6.QtMultimedia',
        'PyQt6.QtNfc',
        'PyQt6.QtOpenGL',
        'PyQt6.QtPositioning',
        'PyQt6.QtQuick',
        'PyQt6.QtRemoteObjects',
        'PyQt6.QtSensors',
        'PyQt6.QtSerialPort',
        'PyQt6.QtSql',
        'PyQt6.QtTest',
        'PyQt6.QtXml',
        'PyQt6.Qt3DCore',
        'PyQt6.Qt3DRender',
        'pygame',
    ],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VisualNovel Studio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VisualNovel Studio',
)
