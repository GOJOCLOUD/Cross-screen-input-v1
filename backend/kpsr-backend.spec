# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(['main.py'],
             pathex=['.'],
             binaries=[],
             datas=[
                 ('data', 'data'),
                 ('../frontend', 'frontend')
             ],
             hiddenimports=[
                 'uvicorn',
                 'fastapi',
                 'pydantic',
                 'pydantic-settings',
                 'typing_extensions',
                 'routes',
                 'routes.clipboard',
                 'routes.shortcut',
                 'routes.button_config',
                 'routes.logs',
                 'routes.monitor',
                 'routes.mouse',
                 'routes.mouse_config',
                 'routes.mouse_listener',
                 'routes.desktop_api',
                 'utils',
                 'utils.clipboard_monitor',
                 'utils.logger',
                 'utils.platform_utils',
                 'utils.port_manager',
                 'utils.shortcut_storage'
             ],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 保留控制台窗口，以便查看启动信息和错误logs
ex = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='kpsr-backend',
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
          icon=None)

# 创建目录结构，便于与Electron集成
coll = COLLECT(ex,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='kpsr-backend')
