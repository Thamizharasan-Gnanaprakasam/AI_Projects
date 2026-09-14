# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['run_gui.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('tones', 'tones'),
        ('.env', '.'),
    ],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'pynput',
        'pynput.keyboard._darwin',
        'pynput.mouse._darwin',
        'Cocoa',
        'AppKit',
        'Quartz',
        'Foundation',
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
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib'],
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

app = BUNDLE(
    coll,
    name='VoiceInk.app',
    icon='assets/icon.icns',
    bundle_identifier='com.voiceink.app',
    info_plist={
        'CFBundleName': 'VoiceInk',
        'CFBundleDisplayName': 'VoiceInk',
        'CFBundleExecutable': 'VoiceInk',
        'CFBundleIdentifier': 'com.voiceink.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSMicrophoneUsageDescription': 'VoiceInk requires microphone access for voice dictation and transcription.',
        'NSAccessibilityUsageDescription': 'VoiceInk requires accessibility access to listen for global hotkeys and inject text at cursor.',
        'NSAppleEventsUsageDescription': 'VoiceInk requires AppleEvents permission to paste transcribed text into the frontmost app.',
        'LSUIElement': False,
        'NSHighResolutionCapable': True,
    },
)
