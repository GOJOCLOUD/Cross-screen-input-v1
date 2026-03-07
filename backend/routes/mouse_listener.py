#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鼠标按键监听服务
监听电脑上的鼠标按键事件，执行对应的快捷键映射
Windows 专用版本（使用 Windows API 钩子）
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import threading
import sys
import os
import platform
import ctypes
from ctypes import wintypes

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入日志模块
from utils.logger import app_logger

from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button

router = APIRouter()

# 键盘控制器
keyboard_controller = KeyboardController()

# 监听器状态
listener_thread = None
is_listening = False
is_windows = platform.system() == 'Windows'

# 权限状态
has_permission = None  # None=未检测, True=有权限, False=无权限
permission_message = ""

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

# Windows API 钩子相关
if is_windows:
    # 导入 Windows API
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    
    # 定义常量
    WH_MOUSE_LL = 14
    WM_LBUTTONDOWN = 0x0201
    WM_RBUTTONDOWN = 0x0204
    WM_MBUTTONDOWN = 0x0207
    WM_XBUTTONDOWN = 0x020B
    HC_ACTION = 0
    
    # 定义结构体
    class POINT(ctypes.Structure):
        _fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG)]
    
    class MSLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [('pt', POINT),
                   ('mouseData', wintypes.DWORD),
                   ('flags', wintypes.DWORD),
                   ('time', wintypes.DWORD),
                   ('dwExtraInfo', ctypes.c_void_p)]
    
    # 钩子回调函数类型 - 使用正确的返回类型
    HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
    
    # 定义 Windows API 函数的参数类型和返回类型
    user32.SetWindowsHookExA.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
    user32.SetWindowsHookExA.restype = wintypes.HANDLE
    
    user32.UnhookWindowsHookEx.argtypes = [wintypes.HANDLE]
    user32.UnhookWindowsHookEx.restype = wintypes.BOOL
    
    user32.CallNextHookEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
    user32.CallNextHookEx.restype = ctypes.c_long
    
    user32.GetMessageA.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HANDLE, wintypes.UINT, wintypes.UINT]
    user32.GetMessageA.restype = wintypes.BOOL
    
    user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.TranslateMessage.restype = wintypes.BOOL
    
    user32.DispatchMessageA.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageA.restype = ctypes.c_long
    
    # 全局钩子句柄
    mouse_hook = None
    
    # 回调函数指针（必须保持全局引用，否则会被垃圾回收）
    mouse_hook_callback_ptr = None
    
    # 侧键数据值
    XBUTTON1 = 0x0001
    XBUTTON2 = 0x0002

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

# 修饰键映射（Windows 专用）
_modifier_map = {
    'ctrl': Key.ctrl, 'cmd': Key.cmd, 'alt': Key.alt, 
    'shift': Key.shift, 'win': Key.cmd,
}

# 特殊键映射（预定义）
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

# Windows 系统命令映射（直接执行系统命令，而不是模拟按键）
import subprocess

# 预编译的命令列表（避免每次都构建命令字符串）
_system_commands = {
    # 系统功能
    'explorer': ['explorer.exe'],
    'desktop': ['explorer.exe', os.path.expanduser('~/Desktop')],
    'downloads': ['explorer.exe', os.path.expanduser('~/Downloads')],
    'documents': ['explorer.exe', os.path.expanduser('~/Documents')],
    
    # 锁屏
    'lock_screen': ['rundll32.exe', 'user32.dll,LockWorkStation'],
    
    # 任务管理器
    'task_manager': ['taskmgr.exe'],
}

# 需要使用 shell 执行的命令
_shell_commands = {
    # 音量控制
    'volume_up': 'powershell -Command "(New-Object -ComObject WScript.Shell).SendKeys([char]175)"',
    'volume_down': 'powershell -Command "(New-Object -ComObject WScript.Shell).SendKeys([char]174)"',
    'volume_mute': 'powershell -Command "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"',
    
    # 播放控制
    'play_pause': 'powershell -Command "(New-Object -ComObject WScript.Shell).SendKeys([char]32)"',
    'next_track': 'powershell -Command "(New-Object -ComObject WScript.Shell).SendKeys([char]176)"',
    'prev_track': 'powershell -Command "(New-Object -ComObject WScript.Shell).SendKeys([char]177)"',
}

def execute_system_command(command_key: str) -> bool:
    """
    执行系统命令
    返回: True 表示执行成功，False 表示命令不存在
    """
    command_key = command_key.lower().strip()
    
    try:
        # 优先使用快速命令（列表形式，无需 shell 解析）
        if command_key in _system_commands:
            subprocess.Popen(
                _system_commands[command_key],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True  # 完全分离进程
            )
            return True
        
        # 使用 shell 命令（较慢但功能更强）
        if command_key in _shell_commands:
            subprocess.Popen(
                _shell_commands[command_key],
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            return True
        
        return False
    except:
        return False

def _parse_shortcut(shortcut: str):
    """解析快捷键（带缓存）"""
    if shortcut in _shortcut_cache:
        return _shortcut_cache[shortcut]
    
    keys = shortcut.lower().split('+')
    modifiers = []
    main_key = None
    
    for k in keys:
        if k in _modifier_map:
            modifiers.append(_modifier_map[k])
        elif len(k) == 1:
            main_key = k
        else:
            main_key = _special_keys.get(k, k)
    
    result = (modifiers, main_key)
    _shortcut_cache[shortcut] = result
    return result

def execute_shortcut_fast(shortcut: str):
    """快速执行快捷键或系统命令（无日志，直接执行）"""
    try:
        shortcut = shortcut.strip().lower()
        
        # 先检查是否是系统命令
        if shortcut in _system_commands or shortcut in _shell_commands:
            execute_system_command(shortcut)
            return
        
        modifiers, main_key = _parse_shortcut(shortcut)
        if main_key is None:
            return
        
        # 按下修饰键
        for mod in modifiers:
            keyboard_controller.press(mod)
        
        # 按下并释放主键
        keyboard_controller.press(main_key)
        keyboard_controller.release(main_key)
        
        # 释放修饰键
        for mod in reversed(modifiers):
            keyboard_controller.release(mod)
    except:
        pass

def execute_shortcut(shortcut: str):
    """执行快捷键或系统命令（带日志，用于调试）"""
    try:
        shortcut = shortcut.strip().lower()
        
        # 先检查是否是系统命令
        if shortcut in _system_commands or shortcut in _shell_commands:
            execute_system_command(shortcut)
            return
        
        modifiers, main_key = _parse_shortcut(shortcut)
        
        if main_key is None:
            app_logger.error(f"快捷键解析失败: {shortcut}", source="mouse_listener")
            return
        
        app_logger.info(f"执行快捷键: {shortcut}", source="mouse_listener")
        
        for mod in modifiers:
            keyboard_controller.press(mod)
        
        keyboard_controller.press(main_key)
        keyboard_controller.release(main_key)
        
        for mod in reversed(modifiers):
            keyboard_controller.release(mod)
            
        app_logger.info(f"快捷键执行完成: {shortcut}", source="mouse_listener")
        
    except Exception as e:
        app_logger.error(f"执行快捷键失败: {e}", source="mouse_listener")

def check_sequence_match(history: list) -> tuple:
    """
    检查按键历史是否匹配任何序列
    返回: (matched_action, is_prefix)
    - matched_action: 匹配到的动作，None 表示没有完全匹配
    - is_prefix: 当前历史是否是某个序列的前缀
    """
    if not history:
        return None, False
    
    history_keys = [h[0] for h in history]
    matched_action = None
    is_prefix = False
    
    for mapping in sequence_mappings:
        seq = mapping['sequence']
        action = mapping['action']
        
        # 完全匹配
        if history_keys == seq:
            matched_action = action
            break
        
        # 检查是否是前缀
        if len(history_keys) < len(seq) and seq[:len(history_keys)] == history_keys:
            is_prefix = True
    
    return matched_action, is_prefix

def execute_pending_single_key():
    """执行待处理的单键操作"""
    global pending_single_key, pending_timer
    
    if pending_single_key:
        key_type, action, _ = pending_single_key
        app_logger.info(f"执行单键操作: {key_type} -> {action}", source="mouse_listener")
        execute_shortcut_fast(action)
        pending_single_key = None
    
    pending_timer = None

def cancel_pending_single_key():
    """取消待处理的单键操作"""
    global pending_single_key, pending_timer
    
    if pending_timer:
        pending_timer.cancel()
        pending_timer = None
    pending_single_key = None

def handle_mouse_button(button_type: str) -> bool:
    """处理鼠标按键事件，返回是否已处理（用于决定是否阻止系统默认行为）"""
    global key_history, pending_single_key, pending_timer
    
    current_time = time.time()
    
    # 清理过期的按键历史
    key_history = [(k, t) for k, t in key_history if current_time - t < SEQUENCE_TIMEOUT]
    
    # 添加当前按键到历史
    key_history.append((button_type, current_time))
    
    # 如果有序列映射，先检查序列匹配
    if sequence_mappings:
        matched_action, is_prefix = check_sequence_match(key_history)
        
        if matched_action:
            # 完全匹配序列，取消待处理的单键，执行序列动作
            cancel_pending_single_key()
            app_logger.info(f"序列匹配: {[h[0] for h in key_history]} -> {matched_action}", source="mouse_listener")
            execute_shortcut_fast(matched_action)
            key_history = []  # 清空历史
            return True
        
        if is_prefix:
            # 当前是某个序列的前缀，取消之前的单键延迟，等待后续按键
            cancel_pending_single_key()
            
            # 如果当前按键有单键映射，设置延迟执行
            if button_type in button_mappings:
                action = button_mappings[button_type]
                pending_single_key = (button_type, action, current_time)
                pending_timer = threading.Timer(SINGLE_KEY_DELAY, execute_pending_single_key)
                pending_timer.start()
                app_logger.info(f"按键 {button_type} 可能是序列前缀，延迟 {SINGLE_KEY_DELAY}s 执行单键操作", source="mouse_listener")
            
            return True  # 阻止默认行为，等待序列完成
    
    # 没有匹配的序列，检查单键映射
    if button_type in button_mappings:
        # 取消之前的待处理单键
        cancel_pending_single_key()
        
        shortcut = button_mappings[button_type]
        execute_shortcut_fast(shortcut)
        key_history = []  # 执行后清空历史
        return True
    
    return False  # 未处理，让系统继续处理

# Windows API 鼠标钩子回调函数
if is_windows:
    def mouse_hook_callback(nCode, wParam, lParam):
        """Windows 鼠标钩子回调函数"""
        if nCode >= 0:
            # 解析鼠标事件
            mouse_info = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            
            # 确定按键类型
            button_type = None
            
            if wParam == WM_LBUTTONDOWN:
                button_type = 'left'
            elif wParam == WM_RBUTTONDOWN:
                button_type = 'right'
            elif wParam == WM_MBUTTONDOWN:
                button_type = 'middle'
            elif wParam == WM_XBUTTONDOWN:
                # 侧键处理
                mouse_data = mouse_info.mouseData >> 16  # 高16位是侧键数据
                if mouse_data == XBUTTON1:
                    button_type = 'side1'
                elif mouse_data == XBUTTON2:
                    button_type = 'side2'
            
            # 检查该按键是否已配置
            if button_type and button_type in button_mappings:
                # 执行我们的操作
                handled = handle_mouse_button(button_type)
                if handled:
                    # 阻止事件传递，返回非零值
                    return 1
        
        # 继续传递事件
        return user32.CallNextHookEx(mouse_hook, nCode, wParam, lParam)

def check_accessibility_permission() -> bool:
    """检测 Windows 权限"""
    global has_permission, permission_message
    try:
        # Windows 上 pynput 通常不需要特殊权限
        has_permission = True
        permission_message = "Windows 系统不需要特殊权限，鼠标侧键功能可用"
        app_logger.info(permission_message, source="mouse_listener")
        return True
    except Exception as e:
        has_permission = False
        permission_message = f"权限检测失败: {e}"
        app_logger.error(permission_message, source="mouse_listener")
        return False

def _run_windows_listener():
    """运行 Windows 监听器"""
    global mouse_hook, is_listening, mouse_hook_callback_ptr
    
    try:
        if is_windows:
            # 在函数内部创建回调函数指针，避免类型不匹配
            mouse_hook_callback_ptr = HOOKPROC(mouse_hook_callback)
            
            # 使用 Windows API 安装鼠标钩子（使用ANSI版本）
            mouse_hook = user32.SetWindowsHookExA(WH_MOUSE_LL, mouse_hook_callback_ptr, None, 0)
            
            if mouse_hook is None:
                app_logger.error("安装鼠标钩子失败", source="mouse_listener")
                is_listening = False
                return
            
            app_logger.info("Windows API 鼠标钩子已安装", source="mouse_listener")
            
            # 消息循环（使用ANSI版本）
            msg = wintypes.MSG()
            while user32.GetMessageA(ctypes.byref(msg), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageA(ctypes.byref(msg))
        else:
            # 非 Windows 系统，使用 pynput
            from pynput.mouse import Listener as PynputListener
            def on_click_pynput(x, y, button, pressed):
                if not pressed:
                    return  # 只处理按下事件
                
                # 映射鼠标按键到统一格式
                button_map = {
                    Button.left: 'left',
                    Button.right: 'right',
                    Button.middle: 'middle',
                    Button.x1: 'side1',
                    Button.x2: 'side2',
                }
                
                button_type = button_map.get(button)
                if button_type:
                    # 检查该按键是否已配置
                    if button_type in button_mappings:
                        # 已配置的按键，执行我们的操作
                        handle_mouse_button(button_type)
                    else:
                        # 未配置的按键，保持原样
                        pass
            
            pynput_listener = PynputListener(on_click=on_click_pynput)
            pynput_listener.start()
            pynput_listener.join()
        
    except Exception as e:
        app_logger.error(f"Windows 监听器异常: {e}", source="mouse_listener")
        is_listening = False
    finally:
        # 清理钩子
        if is_windows and mouse_hook:
            user32.UnhookWindowsHookEx(mouse_hook)
            mouse_hook = None
            mouse_hook_callback_ptr = None
            app_logger.info("Windows API 鼠标钩子已卸载", source="mouse_listener")

def start_listener():
    """启动鼠标监听"""
    global listener_thread, is_listening, has_permission
    
    # 如果已经在运行，重新加载映射（因为配置可能已更新）
    if is_listening:
        load_mappings()
        return {
            'success': True,
            'message': '监听器已在运行，已重新加载配置',
            'permission': has_permission,
            'permission_message': permission_message
        }
    
    # 检查权限
    if not check_accessibility_permission():
        return {
            'success': False,
            'message': '未获得权限，无法启动监听器',
            'permission': has_permission,
            'permission_message': permission_message
        }
    
    # 加载映射
    load_mappings()
    
    # 启动监听线程
    listener_thread = threading.Thread(target=_run_windows_listener, daemon=True)
    listener_thread.start()
    is_listening = True
    
    return {
        'success': True,
        'message': '鼠标监听器启动成功',
        'permission': has_permission,
        'permission_message': permission_message
    }

def stop_listener():
    """停止鼠标监听"""
    global listener_thread, is_listening, mouse_hook, mouse_hook_callback_ptr
    
    if not is_listening:
        return {
            'success': True,
            'message': '监听器未运行'
        }
    
    try:
        # 停止鼠标监听器
        if is_windows and mouse_hook:
            user32.UnhookWindowsHookEx(mouse_hook)
            mouse_hook = None
            mouse_hook_callback_ptr = None
            app_logger.info("Windows API 鼠标钩子已卸载", source="mouse_listener")
        
        is_listening = False
        
        return {
            'success': True,
            'message': '鼠标监听器已停止'
        }
    except Exception as e:
        app_logger.error(f"停止监听器失败: {e}", source="mouse_listener")
        return {
            'success': False,
            'message': f'停止监听器失败: {e}'
        }

def is_listener_running():
    """检查监听器是否正在运行"""
    return is_listening

def reload_mappings():
    """重新加载按键映射"""
    load_mappings()
    return {
        'success': True,
        'message': '按键映射已重新加载',
        'button_mappings': button_mappings,
        'sequence_mappings': sequence_mappings
    }

# API 端点
@router.post("/start")
async def api_start_listener():
    """启动鼠标监听器"""
    return start_listener()

@router.post("/stop")
async def api_stop_listener():
    """停止鼠标监听器"""
    return stop_listener()

@router.get("/status")
async def api_get_status():
    """获取监听器状态"""
    return {
        'is_listening': is_listening,
        'permission': has_permission,
        'permission_message': permission_message,
        'button_mappings_count': len(button_mappings),
        'sequence_mappings_count': len(sequence_mappings)
    }

@router.post("/reload")
async def api_reload_mappings():
    """重新加载按键映射"""
    return reload_mappings()

@router.get("/mappings")
async def api_get_mappings():
    """获取当前按键映射"""
    return {
        'button_mappings': button_mappings,
        'sequence_mappings': sequence_mappings
    }

@router.get("/permission")
async def api_check_permission():
    """检查权限"""
    check_accessibility_permission()
    return {
        'has_permission': has_permission,
        'message': permission_message
    }

@router.get("/platform")
async def api_get_platform():
    """获取平台信息"""
    return {
        "platform": "Windows",
        "system": platform.system(),
        "version": platform.version()
    }
