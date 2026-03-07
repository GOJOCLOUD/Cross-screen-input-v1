#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鼠标按键执行路由
提供鼠标按键执行功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController
import re
import sys
import os

# 添加utils目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import info, error
from utils.platform_utils import get_platform, CURRENT_PLATFORM, MODIFIER_KEY_MAP

# 创建路由器实例
router = APIRouter()

# 初始化控制器
mouse = MouseController()
keyboard = KeyboardController()

# 鼠标按键映射表
MOUSE_BUTTON_MAP = {
    'left': Button.left,
    'right': Button.right,
    'middle': Button.middle,
    'back': 'back',      # 侧键1（后退）
    'forward': 'forward', # 侧键2（前进）
    'side1': 'back',     # 侧键1 别名
    'side2': 'forward',  # 侧键2 别名
}

# 请求模型
class MouseRequest(BaseModel):
    action: str  # 鼠标操作，如 "left" 或 "ctrl+left"

# 响应模型
class MouseResponse(BaseModel):
    status: str
    message: str

# 解析鼠标操作字符串
def parse_mouse_action(action_str):
    """
    解析鼠标操作字符串
    支持格式：
    - "left" - 左键单击
    - "ctrl+left" - Ctrl + 左键单击
    - "left_2" - 左键双击（点击2次）
    - "ctrl+left_3" - Ctrl + 左键三连击
    返回 (修饰键列表, 鼠标按键, 点击次数)
    """
    # 先转换为小写并去除空格
    action_str = action_str.strip().lower()
    
    # 验证格式：必须是小写字母、数字和下划线，用+分隔
    pattern = r'^[a-z0-9_]+(\+[a-z0-9_]+)*$'
    if not re.match(pattern, action_str):
        raise ValueError(f"鼠标操作格式不正确，必须使用小写字母、数字和下划线，用+分隔，例如：left，当前输入：{action_str}")
    
    parts = action_str.split('+')
    modifiers = []
    mouse_action = None
    click_count = 1  # 默认点击1次
    
    for i, part in enumerate(parts):
        part = part.strip()
        
        if i == len(parts) - 1:
            # 最后一个部分是鼠标操作（可能带点击次数后缀）
            # 检查是否有点击次数后缀，如 left_2
            if '_' in part:
                key_parts = part.rsplit('_', 1)
                base_action = key_parts[0]
                try:
                    click_count = int(key_parts[1])
                    if click_count < 1:
                        click_count = 1
                    elif click_count > 10:
                        click_count = 10  # 限制最大点击次数
                except ValueError:
                    # 如果后缀不是数字，把整个部分当作操作名
                    base_action = part
                    click_count = 1
            else:
                base_action = part
            
            # 解析鼠标按键
            if base_action in MOUSE_BUTTON_MAP:
                mouse_action = MOUSE_BUTTON_MAP[base_action]
            elif base_action == 'double_left':
                # 兼容旧的 double_left 格式
                mouse_action = Button.left
                click_count = 2
            elif base_action in ['scroll_up', 'scroll_down']:
                # 滚轮操作特殊处理
                mouse_action = base_action
            else:
                raise ValueError(f"无效的鼠标操作: {base_action}，支持的操作：left, right, middle, back/side1, forward/side2, scroll_up, scroll_down")
        else:
            # 前面的部分是修饰键
            if part in MODIFIER_KEY_MAP:
                modifiers.append(MODIFIER_KEY_MAP[part])
            else:
                raise ValueError(f"无效的修饰键: {part}，支持的修饰键：ctrl, shift, alt")
    
    return modifiers, mouse_action, click_count

# 执行鼠标操作
def execute_mouse_action(action_str):
    """
    执行指定的鼠标操作
    """
    try:
        # 先验证和转换格式
        action_str = action_str.strip().lower()
        
        # 解析鼠标操作
        modifiers, mouse_action, click_count = parse_mouse_action(action_str)
        
        if not mouse_action:
            raise ValueError("鼠标操作解析结果为空")
        
        info(f"执行鼠标操作: action={mouse_action}, modifiers={modifiers}, click_count={click_count}")
        
        # 执行鼠标操作
        try:
            if mouse_action == 'scroll_up':
                # 滚轮向上（click_count 表示滚动量）
                scroll_amount = click_count * 3
                if modifiers:
                    with keyboard.pressed(*modifiers):
                        mouse.scroll(0, scroll_amount)
                else:
                    mouse.scroll(0, scroll_amount)
            elif mouse_action == 'scroll_down':
                # 滚轮向下（click_count 表示滚动量）
                scroll_amount = click_count * 3
                if modifiers:
                    with keyboard.pressed(*modifiers):
                        mouse.scroll(0, -scroll_amount)
                else:
                    mouse.scroll(0, -scroll_amount)
            elif mouse_action == 'back':
                # 侧键后退（使用键盘模拟）
                for _ in range(click_count):
                    if modifiers:
                        with keyboard.pressed(*modifiers):
                            keyboard.press(Key.alt)
                            keyboard.press(Key.left)
                            keyboard.release(Key.left)
                            keyboard.release(Key.alt)
                    else:
                        keyboard.press(Key.alt)
                        keyboard.press(Key.left)
                        keyboard.release(Key.left)
                        keyboard.release(Key.alt)
            elif mouse_action == 'forward':
                # 侧键前进（使用键盘模拟）
                for _ in range(click_count):
                    if modifiers:
                        with keyboard.pressed(*modifiers):
                            keyboard.press(Key.alt)
                            keyboard.press(Key.right)
                            keyboard.release(Key.right)
                            keyboard.release(Key.alt)
                    else:
                        keyboard.press(Key.alt)
                        keyboard.press(Key.right)
                        keyboard.release(Key.right)
                        keyboard.release(Key.alt)
            else:
                # 鼠标按键点击操作（支持点击次数）
                if modifiers:
                    with keyboard.pressed(*modifiers):
                        mouse.click(mouse_action, click_count)
                else:
                    mouse.click(mouse_action, click_count)
        except Exception as e:
            raise ValueError(f"执行鼠标操作失败: {str(e)}")
        
        return True
    except ValueError:
        # 重新抛出 ValueError，让调用者处理
        raise
    except Exception as e:
        raise ValueError(f"执行鼠标操作失败: {str(e)}")

# 执行鼠标操作端点
@router.post("/execute", response_model=MouseResponse)
async def execute_mouse_endpoint(request: MouseRequest):
    """执行鼠标操作"""
    try:
        # 验证鼠标操作格式
        if not request.action:
            error(f"鼠标操作不能为空")
            raise HTTPException(
                status_code=400,
                detail="鼠标操作不能为空"
            )
        
        # 转换为小写格式
        action_str = request.action.strip().lower()
        
        info(f"执行鼠标操作: {action_str}")
        
        # 执行鼠标操作
        execute_mouse_action(action_str)
        
        info(f"鼠标操作执行成功: {action_str}")
        
        return MouseResponse(
            status="success",
            message="鼠标操作执行成功"
        )
    except ValueError as e:
        error(f"鼠标操作执行失败 (ValueError): {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        error(f"鼠标操作执行失败 (Exception): {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"执行鼠标操作失败: {str(e)}"
        )

# 获取支持的鼠标按键列表端点
@router.get("/buttons", response_model=dict)
async def get_mouse_buttons():
    """获取支持的鼠标按键列表"""
    buttons = {
        'basic': [
            {'name': 'left', 'description': '鼠标左键单击'},
            {'name': 'right', 'description': '鼠标右键单击'},
            {'name': 'middle', 'description': '鼠标中键/滚轮键单击'},
        ],
        'side': [
            {'name': 'back', 'description': '鼠标侧键（后退），别名：side1'},
            {'name': 'forward', 'description': '鼠标侧键（前进），别名：side2'},
        ],
        'special': [
            {'name': 'double_left', 'description': '鼠标左键双击'},
            {'name': 'scroll_up', 'description': '滚轮向上滚动'},
            {'name': 'scroll_down', 'description': '滚轮向下滚动'},
        ],
        'examples': [
            {'action': 'left', 'description': '单击左键'},
            {'action': 'ctrl+left', 'description': 'Ctrl + 左键单击'},
            {'action': 'shift+right', 'description': 'Shift + 右键单击'},
            {'action': 'alt+middle', 'description': 'Alt + 中键单击'},
            {'action': 'ctrl+shift+left', 'description': 'Ctrl + Shift + 左键单击'},
        ]
    }
    
    return buttons

# 获取平台信息端点
@router.get("/platform", response_model=dict)
async def get_platform_info():
    """获取当前操作系统平台信息"""
    platform = get_platform()
    
    # 平台特定的鼠标操作建议
    suggestions = {
        'windows': {
            'left_click': 'left',
            'right_click': 'right',
            'middle_click': 'middle',
            'back_button': 'back',
            'forward_button': 'forward',
            'double_click': 'double_left',
            'scroll_up': 'scroll_up',
            'scroll_down': 'scroll_down',
        },
        'macos': {
            'left_click': 'left',
            'right_click': 'right',
            'middle_click': 'middle',
            'back_button': 'back',
            'forward_button': 'forward',
            'double_click': 'double_left',
            'scroll_up': 'scroll_up',
            'scroll_down': 'scroll_down',
        },
        'linux': {
            'left_click': 'left',
            'right_click': 'right',
            'middle_click': 'middle',
            'back_button': 'back',
            'forward_button': 'forward',
            'double_click': 'double_left',
            'scroll_up': 'scroll_up',
            'scroll_down': 'scroll_down',
        }
    }
    
    return {
        'platform': platform,
        'suggestions': suggestions.get(platform, {}),
        'note': '在 macOS 上，ctrl 会自动映射到 cmd（Command键）。如果需要真正的 Control 键，请使用 ctrl_l 或 ctrl_r。'
    }