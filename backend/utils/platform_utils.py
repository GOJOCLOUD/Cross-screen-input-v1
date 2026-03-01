#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平台工具模块
Windows专用实现
"""

from pynput.keyboard import Key

# Windows专用常量
CURRENT_PLATFORM = 'windows'
IS_WINDOWS = True
IS_MAC = False
IS_LINUX = False


def get_platform():
    """
    检测操作系统平台
    返回: 'windows' (本版本仅支持Windows)
    """
    return 'windows'


def get_modifier_key_map():
    """
    获取Windows平台特定的修饰键映射
    """
    return {
        'ctrl': Key.ctrl,   # Windows 上 ctrl 映射到 Control
        'cmd': Key.cmd,     # cmd 映射到 Windows键
        'win': Key.cmd,     # win 映射到 Windows键
        'shift': Key.shift,
        'alt': Key.alt,
    }


# 预加载修饰键映射（避免每次调用都重新创建）
MODIFIER_KEY_MAP = get_modifier_key_map()


__all__ = [
    'get_platform',
    'get_modifier_key_map',
    'CURRENT_PLATFORM',
    'IS_WINDOWS', 
    'IS_MAC',
    'IS_LINUX',
    'MODIFIER_KEY_MAP',
]
