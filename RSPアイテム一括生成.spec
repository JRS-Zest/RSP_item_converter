# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['RSPアイテム一括生成.py'],
    pathex=[],
    binaries=[],
    datas=[('複合itemdatからjson抽出.py', '.'), ('rsp_tooltip_generator.py', '.'), ('render_rsp_items.py', '.'), ('アイテム表示用HTMLベース.html', '.')],
    hiddenimports=[],
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
    name='RSPアイテム一括生成',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
