# -*- mode: python ; coding: utf-8 -*-
# Windows PyInstaller Build Specification for VoiceInk

block_cipher = None

import os

extra_datas = [
    ('assets', 'assets'),
    ('tones', 'tones'),
]
if os.path.exists('.env'):
    extra_datas.append(('.env', '.'))
elif os.path.exists('.env.example'):
    extra_datas.append(('.env.example', '.'))

a = Analysis(
    ['run_gui.py'],
    pathex=['.'],
    binaries=[],
    datas=extra_datas,
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'pynput',
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        'sounddevice',
        'scipy',
        'scipy.signal',
        'scipy.io',
        'scipy.io.wavfile',
        'numpy',
        'dotenv',
        'sqlite3',
        'httpx',
        'certifi',
        'requests',
        'noisereduce',
        'PIL',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'torch',
        'torchvision',
        'torchaudio',
        'Cocoa',
        'AppKit',
        'Quartz',
        'Foundation',
        'objc',
        'mlx',
        'mlx_whisper',
        'mlx_lm',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VoiceInk',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='VoiceInk',
)
