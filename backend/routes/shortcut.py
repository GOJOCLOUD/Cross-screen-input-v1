#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快捷键执行路由
提供键盘快捷键执行功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pynput.keyboard import Key, Controller
import re
import sys
import os

# 添加utils目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import info, error
from utils.platform_utils import get_platform, CURRENT_PLATFORM, MODIFIER_KEY_MAP

# 创建路由器实例
router = APIRouter()

# 初始化键盘控制器
keyboard = Controller()

# 基础按键映射表（平台无关）
BASE_KEY_MAP = {
    # 修饰键（平台无关部分）
    'alt': Key.alt,
    'shift': Key.shift,
    
    # 方向键
    'up': Key.up,
    'down': Key.down,
    'left': Key.left,
    'right': Key.right,
    
    # 编辑键
    'backspace': Key.backspace,
    'delete': Key.delete,
    'del': Key.delete,  # 别名
    
    # 导航键
    'home': Key.home,
    'end': Key.end,
    'pageup': Key.page_up,
    'pagedown': Key.page_down,
    'pgup': Key.page_up,  # 别名
    'pgdn': Key.page_down,  # 别名
    
    # 特殊键
    'esc': Key.esc,
    'escape': Key.esc,  # 别名
    'enter': Key.enter,
    'return': Key.enter,  # 别名
    'tab': Key.tab,
    'space': Key.space,
    
    # 锁定键
    'caps_lock': Key.caps_lock,
    
    # 媒体键
    'volume_up': Key.media_volume_up,
    'volume_down': Key.media_volume_down,
    'volume_mute': Key.media_volume_mute,
    'play_pause': Key.media_play_pause,
    'next': Key.media_next,
    'previous': Key.media_previous,
}

# 合并映射表（使用公共模块的修饰键映射）
KEY_MAP = {**BASE_KEY_MAP, **MODIFIER_KEY_MAP}

# 请求模型
class ShortcutRequest(BaseModel):
    shortcut: str
    action_type: str  # "single" | "multi" | "toggle"

# 响应模型
class ShortcutResponse(BaseModel):
    status: str
    message: str

# 解析快捷键字符串
def parse_shortcut(shortcut_str):
    """
    解析 "ctrl+v" 格式的快捷键（小写格式）
    根据平台自动映射：Windows上 ctrl->Control，macOS上 ctrl->Command
    返回 pynput 的键对象列表
    """
    # 先转换为小写并去除空格
    shortcut_str = shortcut_str.strip().lower()
    
    # 验证格式：必须是小写字母、数字和下划线，用+分隔
    pattern = r'^[a-z0-9_]+(\+[a-z0-9_]+)*$'
    if not re.match(pattern, shortcut_str):
        raise ValueError(f"快捷键格式不正确，必须使用小写字母、数字和下划线，用+分隔，例如：ctrl+v，当前输入：{shortcut_str}")
    
    parts = shortcut_str.split('+')
    keys = []
    
    for part in parts:
        part = part.strip()
        
        # 1. 先查映射表
        if part in KEY_MAP:
            keys.append(KEY_MAP[part])
        # 2. 功能键（f1-f20）
        elif part.startswith('f') and len(part) > 1 and part[1:].isdigit():
            f_num = part[1:]
            f_key = getattr(Key, f'f{f_num}', None)
            if f_key:
                keys.append(f_key)
            else:
                raise ValueError(f"无效的功能键: {part}，支持 f1-f20")
        # 3. 字母和数字（单个字符）
        elif len(part) == 1 and part.isalnum():
            keys.append(part)
        else:
            raise ValueError(f"无效的按键: {part}，支持的按键请查看文档")
    
    return keys

# 执行快捷键
def execute_shortcut(shortcut_str):
    """
    执行指定的快捷键
    """
    try:
        # 先验证和转换格式
        shortcut_str = shortcut_str.strip().lower()
        
        # 解析快捷键
        keys = parse_shortcut(shortcut_str)
        
        if not keys:
            raise ValueError("快捷键解析结果为空")
        
        # 执行快捷键
        try:
            if len(keys) == 1:
                # 单个键
                keyboard.press(keys[0])
                keyboard.release(keys[0])
            else:
                # 组合键
                with keyboard.pressed(*keys[:-1]):
                    keyboard.press(keys[-1])
                    keyboard.release(keys[-1])
        except Exception as e:
            raise ValueError(f"执行按键操作失败: {str(e)}")
        
        return True
    except ValueError:
        # 重新抛出 ValueError，让调用者处理
        raise
    except Exception as e:
        raise ValueError(f"执行快捷键失败: {str(e)}")

# 执行快捷键端点
@router.post("/execute", response_model=ShortcutResponse)
async def execute_shortcut_endpoint(request: ShortcutRequest):
    """执行键盘快捷键"""
    try:
        # 验证快捷键格式
        if not request.shortcut:
            error(f"快捷键不能为空")
            raise HTTPException(
                status_code=400,
                detail="快捷键不能为空"
            )
        
        # 转换为小写格式
        shortcut_str = request.shortcut.strip().lower()
        
        info(f"执行快捷键: {shortcut_str} (类型: {request.action_type})")
        
        # 执行快捷键
        execute_shortcut(shortcut_str)
        
        info(f"快捷键执行成功: {shortcut_str}")
        
        return ShortcutResponse(
            status="success",
            message="快捷键执行成功"
        )
    except ValueError as e:
        error(f"快捷键执行失败 (ValueError): {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        error(f"快捷键执行失败 (Exception): {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"执行快捷键失败: {str(e)}"
        )

# 获取平台信息端点
@router.get("/platform", response_model=dict)
async def get_platform_info():
    """获取当前操作系统平台信息"""
    platform = get_platform()
    
    # 平台特定的快捷键建议
    suggestions = {
        'windows': {
            'copy': 'ctrl+c',
            'paste': 'ctrl+v',
            'cut': 'ctrl+x',
            'select_all': 'ctrl+a',
            'undo': 'ctrl+z',
            'redo': 'ctrl+y',
            'save': 'ctrl+s',
        },
        'macos': {
            'copy': 'cmd+c',  # 注意：macOS 使用 cmd
            'paste': 'cmd+v',
            'cut': 'cmd+x',
            'select_all': 'cmd+a',
            'undo': 'cmd+z',
            'redo': 'cmd+shift+z',
            'save': 'cmd+s',
        },
        'linux': {
            'copy': 'ctrl+c',
            'paste': 'ctrl+v',
            'cut': 'ctrl+x',
            'select_all': 'ctrl+a',
            'undo': 'ctrl+z',
            'redo': 'ctrl+y',
            'save': 'ctrl+s',
        }
    }
    
    return {
        'platform': platform,
        'suggestions': suggestions.get(platform, {}),
        'note': '在 macOS 上，ctrl 会自动映射到 cmd（Command键）。如果需要真正的 Control 键，请使用 ctrl_l 或 ctrl_r。'
    }
