#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes包初始化文件
"""

# 导出路由模块
from . import clipboard
from . import shortcut
from . import button_config
from . import logs
from . import monitor
from . import mouse
from . import mouse_config
from . import mouse_listener
from . import desktop_api

__all__ = [
    "clipboard",
    "shortcut",
    "button_config",
    "logs",
    "monitor",
    "mouse",
    "mouse_config",
    "mouse_listener",
    "desktop_api",
]
