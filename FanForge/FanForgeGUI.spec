# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


ROOT = Path(SPECPATH)

datas = [
    (str(ROOT / "configs"), "configs"),
    (str(ROOT / "core" / "hs2811_fan_core.c.in"), "core"),
    (
        str(ROOT / "fanforge" / "chips" / "hs2811_sop16.json"),
        "fanforge/chips",
    ),
]
datas += collect_data_files("customtkinter")

a = Analysis(
    [str(ROOT / "fanforge_gui" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=["customtkinter"],
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
    name="FanForge",
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
)
