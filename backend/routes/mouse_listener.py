#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鼠标按键监听服务
监听电脑上的鼠标按键事件，执行对应的快捷键映射
Windows专用实现
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import threading
import sys
import os

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入日志模块
from utils.logger import app_logger

from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Listener

router = APIRouter()

# 键盘控制器
keyboard_controller = KeyboardController()

# 监听器状态
listener_thread = None
is_listening = False

# 鼠标按键映射
button_mappings = {}  # 单键映射: {keyType: action}
sequence_mappings = []  # 序列映射: [{sequence: [key1, key2], action: action}, ...]

# 按键序列检测相关
import time
key_history = []  # 按键历史: [(key_type, timestamp), ...]
SEQUENCE_TIMEOUT = 0.5  # 序列超时时间（秒）
SINGLE_KEY_DELAY = 0.3  # 单键延迟时间（秒），等待可能的后续按键
pending_single_key = None  # 待处理的单键: (key_type, action, timestamp)
pending_timer = None  # 待处理的定时器

def load_mappings():
    """从配置文件加载鼠标按键映射（支持单键和序列）"""
    global button_mappings, sequence_mappings
    try:
        from routes.mouse_config import load_buttons
        buttons = load_buttons()
        button_mappings = {}
        sequence_mappings = []
        
        for btn in buttons:
            action = btn.get('action')
            if not action:
                continue
                
            # 检查是否是序列配置
            sequence = btn.get('sequence')
            if sequence and isinstance(sequence, list) and len(sequence) > 0:
                # 序列映射
                sequence_mappings.append({
                    'sequence': sequence,
                    'action': action,
                    'name': btn.get('name', '')
                })
            else:
                # 单键映射（向后兼容）
                key_type = btn.get('keyType')
                if key_type:
                    button_mappings[key_type] = action
        
        # 按序列长度降序排序（长序列优先匹配）
        sequence_mappings.sort(key=lambda x: len(x['sequence']), reverse=True)
        
        app_logger.info(f"加载了 {len(button_mappings)} 个单键映射: {button_mappings}", source="mouse_listener")
        app_logger.info(f"加载了 {len(sequence_mappings)} 个序列映射: {[m['sequence'] for m in sequence_mappings]}", source="mouse_listener")
    except Exception as e:
        app_logger.error(f"加载映射失败: {e}", source="mouse_listener")
        button_mappings = {}
        sequence_mappings = []

# 预解析的快捷键缓存，避免每次都解析
_shortcut_cache = {}

# Windows修饰键映射
_modifier_map_win = {
    'ctrl': Key.ctrl, 'cmd': Key.cmd, 'alt': Key.alt,
    'shift': Key.shift, 'win': Key.cmd,
}
_modifier_map = _modifier_map_win

# 特殊键映射
_special_keys = {
    'enter': Key.enter, 'tab': Key.tab, 'space': Key.space,
    'backspace': Key.backspace, 'delete': Key.delete,
    'escape': Key.esc, 'esc': Key.esc,
    'up': Key.up, 'down': Key.down, 'left': Key.left, 'right': Key.right,
    'home': Key.home, 'end': Key.end,
    'pageup': Key.page_up, 'pagedown': Key.page_down,
    'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4,
    'f5': Key.f5, 'f6': Key.f6, 'f7': Key.f7, 'f8': Key.f8,
    'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
}

def _parse_shortcut(shortcut: str):
    """
    解析快捷键字符串为按键列表
    支持格式：ctrl+c, ctrl+shift+alt+delete, f1, enter 等
    """
    # 检查缓存
    if shortcut in _shortcut_cache:
        return _shortcut_cache[shortcut]
    
    keys = []
    parts = shortcut.lower().split('+')
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        # 检查修饰键
        if part in _modifier_map:
            keys.append(_modifier_map[part])
        # 检查特殊键
        elif part in _special_keys:
            keys.append(_special_keys[part])
        # 检查功能键
        elif part.startswith('f') and len(part) > 1:
            try:
                f_num = int(part[1:])
                if 1 <= f_num <= 20:
                    f_key = getattr(Key, f'f{f_num}', None)
                    if f_key:
                        keys.append(f_key)
                    else:
                        raise ValueError(f"无效的功能键: {part}，支持 f1-f20")
                else:
                    raise ValueError(f"无效的功能键: {part}，支持 f1-f20")
            except ValueError:
                raise ValueError(f"无效的功能键: {part}，支持 f1-f20")
        # 普通字符键
        elif len(part) == 1:
            keys.append(part)
        else:
            raise ValueError(f"无效的按键: {part}，支持的按键请查看文档")
    
    if not keys:
        raise ValueError("快捷键不能为空")
    
    # 缓存结果
    _shortcut_cache[shortcut] = keys
    return keys

def execute_shortcut_fast(shortcut: str):
    """
    快速执行快捷键（无日志）
    """
    try:
        keys = _parse_shortcut(shortcut)
        
        # 按下所有键
        for key in keys:
            keyboard_controller.press(key)
        
        # 释放所有键
        for key in reversed(keys):
            keyboard_controller.release(key)
            
        return True
    except Exception:
        return False

def execute_shortcut(shortcut: str):
    """
    执行快捷键
    """
    try:
        keys = _parse_shortcut(shortcut)
        
        app_logger.info(f"执行快捷键: {shortcut}", source="mouse_listener")
        
        # 按下所有键
        for key in keys:
            keyboard_controller.press(key)
        
        # 释放所有键
        for key in reversed(keys):
            keyboard_controller.release(key)
            
        app_logger.info(f"快捷键执行成功: {shortcut}", source="mouse_listener")
        return True
    except ValueError as e:
        app_logger.error(f"快捷键执行失败 (ValueError): {str(e)}", source="mouse_listener")
        raise ValueError(f"执行快捷键失败: {str(e)}")
    except Exception as e:
        app_logger.error(f"快捷键执行失败 (Exception): {str(e)}", source="mouse_listener")
        raise ValueError(f"执行快捷键失败: {str(e)}")

def check_sequence_match(history: list) -> tuple:
    """
    检查按键历史是否匹配任何序列
    返回: (匹配的序列映射, 剩余历史)
    """
    # 只取最近的按键
    recent_history = history[-20:]  # 最多检查最近20个按键
    
    for mapping in sequence_mappings:
        sequence = mapping['sequence']
        if len(sequence) > len(recent_history):
            continue
            
        # 检查是否匹配序列
        matched = True
        for i, seq_key in enumerate(sequence):
            hist_key = recent_history[len(recent_history) - len(sequence) + i][0]
            if hist_key != seq_key:
                matched = False
                break
                
        if matched:
            # 返回匹配的映射和剩余历史（去掉匹配的部分）
            remaining = recent_history[:len(recent_history) - len(sequence)]
            return mapping, remaining
            
    return None, recent_history

def execute_pending_single_key():
    """执行待处理的单键"""
    global pending_single_key, pending_timer
    
    if pending_single_key:
        key_type, action, timestamp = pending_single_key
        pending_single_key = None
        pending_timer = None
        
        try:
            execute_shortcut(action)
            app_logger.info(f"执行单键映射: {key_type} -> {action}", source="mouse_listener")
        except Exception as e:
            app_logger.error(f"执行单键映射失败: {e}", source="mouse_listener")

def cancel_pending_single_key():
    """取消待处理的单键"""
    global pending_single_key, pending_timer
    
    if pending_timer:
        pending_timer.cancel()
        pending_timer = None
    
    pending_single_key = None

def handle_mouse_button(button_number: int) -> bool:
    """
    处理鼠标按键事件
    返回是否成功处理
    """
    # Windows: 0=左键, 1=右键, 2=中键, 3=侧键1(后退), 4=侧键2(前进)
    key_type = f"button_{button_number}"
    
    # 记录按键历史
    current_time = time.time()
    key_history.append((key_type, current_time))
    
    # 清理过期的历史记录
    while key_history and key_history[0][1] < current_time - SEQUENCE_TIMEOUT:
        key_history.pop(0)
    
    # 检查序列匹配
    matched_mapping, remaining_history = check_sequence_match(key_history)
    
    if matched_mapping:
        # 取消待处理的单键
        cancel_pending_single_key()
        
        # 执行序列映射
        try:
            execute_shortcut(matched_mapping['action'])
            app_logger.info(f"执行序列映射: {matched_mapping['sequence']} -> {matched_mapping['action']}", source="mouse_listener")
            
            # 清空按键历史
            key_history.clear()
            return True
        except Exception as e:
            app_logger.error(f"执行序列映射失败: {e}", source="mouse_listener")
    
    # 检查单键映射
    elif key_type in button_mappings:
        action = button_mappings[key_type]
        
        # 取消之前的待处理单键
        cancel_pending_single_key()
        
        # 设置新的待处理单键
        pending_single_key = (key_type, action, current_time)
        
        # 设置定时器，延迟执行单键
        import threading
        pending_timer = threading.Timer(SINGLE_KEY_DELAY, execute_pending_single_key)
        pending_timer.start()
        
        app_logger.info(f"检测到单键映射: {key_type} -> {action} (延迟执行)", source="mouse_listener")
        return True
    
    return False

def _on_click(x, y, button, pressed):
    """鼠标点击事件回调"""
    if not pressed:  # 只处理按键释放事件
        try:
            # 获取按钮编号
            if hasattr(button, 'value'):
                button_number = button.value
            else:
                # 兼容不同版本的pynput
                button_map = {
                    'Button.left': 0,
                    'Button.right': 1,
                    'Button.middle': 2,
                    'Button.x1': 3,
                    'Button.x2': 4,
                }
                button_str = str(button)
                button_number = button_map.get(button_str, 0)
            
            # 处理按键
            handle_mouse_button(button_number)
            
        except Exception as e:
            app_logger.error(f"处理鼠标按键失败: {e}", source="mouse_listener")

def _run_windows_listener():
    """运行Windows监听器"""
    try:
        with Listener(on_click=_on_click) as listener:
            app_logger.info("Windows监听器已启动", source="mouse_listener")
            listener.join()
    except Exception as e:
        app_logger.error(f"Windows监听器异常: {e}", source="mouse_listener")

def start_listener():
    """启动鼠标按键监听器"""
    global listener_thread, is_listening
    
    if is_listening:
        return {'success': False, 'message': '监听器已在运行'}
    
    # 加载映射
    load_mappings()
    
    # 启动监听线程
    listener_thread = threading.Thread(target=_run_windows_listener, daemon=True)
    listener_thread.start()
    
    # 等待一小段时间确保线程启动
    time.sleep(0.1)
    
    is_listening = True
    return {'success': True, 'message': '监听器启动成功'}

def stop_listener():
    """停止鼠标按键监听器"""
    global is_listening
    
    if not is_listening:
        return {'success': False, 'message': '监听器未运行'}
    
    # 取消待处理的单键
    cancel_pending_single_key()
    
    # 清空按键历史
    key_history.clear()
    
    is_listening = False
    return {'success': True, 'message': '监听器停止成功'}

# API 端点
class ListenerStatus(BaseModel):
    running: bool
    message: str
    platform: str

@router.get("/status", response_model=ListenerStatus)
async def get_listener_status():
    """获取监听器状态"""
    return ListenerStatus(
        running=is_listening,
        message="监听器正在运行" if is_listening else "监听器已停止",
        platform="Windows"
    )

@router.get("/check-permission")
async def check_permission():
    """检查权限（Windows不需要特殊权限）"""
    return {
        "has_permission": True,
        "message": "Windows系统不需要特殊权限",
        "platform": "Windows"
    }

@router.post("/start")
async def start_mouse_listener():
    """启动鼠标监听器"""
    return start_listener()

@router.post("/stop")
async def stop_mouse_listener():
    """停止鼠标监听器"""
    return stop_listener()

@router.post("/reload")
async def reload_mappings_endpoint():
    """重新加载映射配置"""
    load_mappings()
    return {"message": "映射配置已重新加载"}

@router.get("/system-commands")
async def get_system_commands():
    """获取可用的系统命令列表（Windows版本）"""
    return {
        "platform": "Windows",
        "system_commands": [],
        "message": "Windows版本不支持系统命令"
    }

def is_listener_running() -> bool:
    """检查监听器是否正在运行"""
    return is_listening

def reload_and_restart_listener():
    """重新加载配置并重启监听器"""
    if is_listening:
        stop_listener()
        time.sleep(0.5)
    return start_listener()