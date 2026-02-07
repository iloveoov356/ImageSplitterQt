# -*- mode: python -*-
import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hiddenimports = collect_submodules("PySide6")


a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('src/i18n/locales/*.json', 'i18n/locales')],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ImageSplitterQt',
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

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name='ImageSplitterQt.app',
        icon=None,
        bundle_identifier='local.imagesplitter.app',
    )
    coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=True, name='ImageSplitterQt')
else:
    coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=True, name='ImageSplitterQt')
