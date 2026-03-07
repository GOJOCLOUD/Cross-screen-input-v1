#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils 工具包
提供日志、平台检测、剪贴板监听等通用功能

注意：为避免循环导入，各模块应直接从子模块导入：
    from utils.logger import info, error
    from utils.platform_utils import get_platform, MODIFIER_KEY_MAP
"""

# 不在 __init__ 中自动导入，避免循环导入问题
# 需要时请直接从子模块导入

__all__ = [
    'logger',
    'platform_utils',
    'clipboard_monitor',
    'shortcut_storage',
    'log_reader',
]
