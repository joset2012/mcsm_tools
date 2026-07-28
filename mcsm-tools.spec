# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/home/meversation/CodeProject/mcsm-tools/run.py'],
    pathex=[],
    binaries=[],
    datas=[('/home/meversation/CodeProject/mcsm-tools/mcsm_tools/fonts', 'mcsm_tools/fonts')],
    hiddenimports=['engineio', 'engineio.client', 'prompt_toolkit', 'requests', 'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='mcsm-tools',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
