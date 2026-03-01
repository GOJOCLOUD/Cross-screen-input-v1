#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鼠标按键监听服务
监听电脑上的鼠标按键事件，执行对应的快捷键映射
支持 macOS（使用 Quartz）和 Windows（使用 pynput）
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import threading
import sys
import os
import platform

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入日志模块
from utils.logger import app_logger

from pynput.keyboard import Key, Controller as KeyboardController

router = APIRouter()

# 键盘控制器
keyboard_controller = KeyboardController()


# 监听器状态
listener_thread = None
is_listening = False
is_mac = platform.system() == 'Darwin'

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

# 修饰键映射（预定义）
_modifier_map_mac = {
    'ctrl': Key.cmd, 'cmd': Key.cmd, 'alt': Key.alt, 
    'shift': Key.shift, 'win': Key.cmd,
}
_modifier_map_win = {
    'ctrl': Key.ctrl, 'cmd': Key.cmd, 'alt': Key.alt,
    'shift': Key.shift, 'win': Key.cmd,
}
_modifier_map = _modifier_map_mac if is_mac else _modifier_map_win

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

# macOS 系统命令映射（直接执行系统命令，而不是模拟按键）
import subprocess

# 预编译的命令列表（避免每次都构建命令字符串）
_system_commands = {
    # 启动台和调度中心（使用更快的方式）
    'launchpad': ['open', '-a', 'Launchpad'],
    'mission_control': ['open', '-a', 'Mission Control'],
    'mission': ['open', '-a', 'Mission Control'],
    
    # 截图工具
    'screenshot': ['screencapture', '-i', '-c'],
    'screenshot_area': ['screencapture', '-i', '-c'],
    'screenshot_window': ['screencapture', '-i', '-w', '-c'],
    'screenshot_full': ['screencapture', '-c'],
    
    # Finder
    'finder': ['open', '-a', 'Finder'],
    'desktop': ['open', os.path.expanduser('~/Desktop')],
    'downloads': ['open', os.path.expanduser('~/Downloads')],
    'documents': ['open', os.path.expanduser('~/Documents')],
    
    # Siri
    'siri': ['open', '-a', 'Siri'],
    
    # 锁屏和睡眠
    'sleep': ['pmset', 'sleepnow'],
}

# 需要使用 shell 执行的命令（osascript 等较慢的命令）
_shell_commands = {
    # 系统功能（osascript 较慢但功能强大）
    'spotlight': 'osascript -e \'tell application "System Events" to keystroke space using command down\'',
    'notification_center': 'open -g "x-apple.systempreferences:com.apple.preference.notifications"',
    'notification': 'open -g "x-apple.systempreferences:com.apple.preference.notifications"',
    'dictation': 'osascript -e \'tell application "System Events" to keystroke "d" using {command down, fn down}\'',
    
    # 音量控制
    'volume_up': 'osascript -e "set volume output volume (output volume of (get volume settings) + 10)"',
    'volume_down': 'osascript -e "set volume output volume (output volume of (get volume settings) - 10)"',
    'volume_mute': 'osascript -e "set volume output muted not (output muted of (get volume settings))"',
    
    # 播放控制
    'play_pause': 'osascript -e \'tell application "System Events" to key code 16 using {command down, option down}\'',
    'next_track': 'osascript -e \'tell application "System Events" to key code 17 using {command down, option down}\'',
    'prev_track': 'osascript -e \'tell application "System Events" to key code 18 using {command down, option down}\'',
    
    # 锁屏
    'lock_screen': 'osascript -e \'tell application "System Events" to keystroke "q" using {command down, control down}\'',
    
    # 显示桌面
    'show_desktop': 'osascript -e \'tell application "System Events" to key code 103\'',
}

def execute_system_command(command_key: str) -> bool:
    """
    执行系统命令（优化版：快速命令使用列表形式，避免 shell 解析开销）
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
        
        # 先检查是否是系统命令（仅 macOS）
        if is_mac and shortcut in _system_commands:
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
        
        # 先检查是否是系统命令（仅 macOS）
        if is_mac and shortcut in _system_commands:
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

def handle_mouse_button(button_number: int) -> bool:
    """处理鼠标按键事件，返回是否已处理（用于决定是否阻止系统默认行为）"""
    global key_history, pending_single_key, pending_timer
    
    # 按键编号映射
    # macOS: 0=左键, 1=右键, 2=中键, 3=侧键1(后退), 4=侧键2(前进)
    button_map = {
        0: 'left',
        1: 'right', 
        2: 'middle',
        3: 'side1',
        4: 'side2',
    }
    
    button_type = button_map.get(button_number)
    if not button_type:
        return False
    
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

# macOS 专用监听器
if is_mac:
    import Quartz
    from Quartz import (
        CGEventTapCreate, CGEventTapEnable, CGEventTapIsEnabled,
        kCGSessionEventTap, kCGHeadInsertEventTap, kCGEventTapOptionDefault,
        kCGEventTapOptionListenOnly,
        CGEventMaskBit, kCGEventOtherMouseDown,
        CGEventGetIntegerValueField, kCGMouseEventButtonNumber,
        CFMachPortCreateRunLoopSource, CFRunLoopGetCurrent, CFRunLoopAddSource,
        kCFRunLoopCommonModes, CFRunLoopRun, CFRunLoopStop
    )
    
    _run_loop = None
    _tap = None
    
    def check_accessibility_permission() -> bool:
        """检测 macOS 辅助功能权限"""
        global has_permission, permission_message
        try:
            # 尝试创建一个测试用的事件 tap
            test_tap = CGEventTapCreate(
                kCGSessionEventTap,
                kCGHeadInsertEventTap,
                kCGEventTapOptionListenOnly,  # 只监听，权限要求更低
                CGEventMaskBit(kCGEventOtherMouseDown),
                lambda *args: args[2],  # 空回调
                None
            )
            if test_tap is not None:
                has_permission = True
                permission_message = "已获得辅助功能权限，鼠标侧键功能可用"
                app_logger.info(permission_message, source="mouse_listener")
                return True
            else:
                has_permission = False
                permission_message = "未获得辅助功能权限，鼠标侧键功能不可用。请在 系统设置 > 隐私与安全性 > 辅助功能 中授权本程序"
                app_logger.warning(permission_message, source="mouse_listener")
                return False
        except Exception as e:
            has_permission = False
            permission_message = f"权限检测失败: {e}"
            app_logger.error(permission_message, source="mouse_listener")
            return False
    
    def _mouse_callback(proxy, event_type, event, refcon):
        """macOS 鼠标事件回调 - 极速版"""
        global _tap
        # 确保 tap 始终启用（系统可能因回调超时而禁用）
        if _tap and not CGEventTapIsEnabled(_tap):
            CGEventTapEnable(_tap, True)
        
        try:
            button_number = CGEventGetIntegerValueField(event, kCGMouseEventButtonNumber)
            handled = handle_mouse_button(button_number)
            if handled:
                # 返回 None 阻止事件传递给系统，避免触发系统默认行为（如前进/后退）
                return None
        except:
            pass
        return event
    
    def _run_macos_listener():
        """运行 macOS 监听器"""
        global _run_loop, _tap, is_listening
        
        try:
            # 监听所有鼠标按下事件（包括侧键）
            mask = CGEventMaskBit(kCGEventOtherMouseDown)
            
            # kCGSessionEventTap + kCGHeadInsertEventTap = 会话级最高优先级
            # kCGHIDEventTap 需要 root 权限，普通应用无法使用
            _tap = CGEventTapCreate(
                kCGSessionEventTap,       # 会话级别（普通权限可用的最高级别）
                kCGHeadInsertEventTap,    # 插入队列头部，优先于其他 tap
                kCGEventTapOptionDefault, # 可以修改/阻止事件
                mask,
                _mouse_callback,
                None
            )
            
            if _tap is None:
                app_logger.error("创建事件 tap 失败，请检查辅助功能权限", source="mouse_listener")
                is_listening = False
                return
            
            CGEventTapEnable(_tap, True)
            
            source = CFMachPortCreateRunLoopSource(None, _tap, 0)
            _run_loop = CFRunLoopGetCurrent()
            CFRunLoopAddSource(_run_loop, source, kCFRunLoopCommonModes)
            
            app_logger.info("macOS 监听器已启动", source="mouse_listener")
            CFRunLoopRun()
            
        except Exception as e:
            app_logger.error(f"macOS 监听器异常: {e}", source="mouse_listener")
            is_listening = False

# Windows 专用监听器
else:
    from pynput import mouse as pynput_mouse
    _pynput_listener = None
    
    def check_accessibility_permission() -> bool:
        """检测 Windows 权限（通常不需要特殊权限）"""
        global has_permission, permission_message
        try:
            # Windows 上 pynput 通常不需要特殊权限
            # 但某些情况下可能需要管理员权限
            has_permission = True
            permission_message = "Windows 系统，鼠标侧键功能可用"
            app_logger.info(permission_message, source="mouse_listener")
            return True
        except Exception as e:
            has_permission = False
            permission_message = f"权限检测失败: {e}"
            app_logger.error(permission_message, source="mouse_listener")
            return False
    
    def _on_click(x, y, button, pressed):
        """pynput 鼠标点击回调"""
        if not pressed:
            return
        
        button_map = {
            pynput_mouse.Button.left: 0,
            pynput_mouse.Button.right: 1,
            pynput_mouse.Button.middle: 2,
        }
        
        button_number = button_map.get(button)
        
        # 尝试识别侧键
        if button_number is None:
            button_str = str(button).lower()
            if 'x1' in button_str or 'back' in button_str:
                button_number = 3
            elif 'x2' in button_str or 'forward' in button_str:
                button_number = 4
            else:
                return
        
        # pynput 在 Windows 上需要使用 suppress 参数来阻止事件
        # 这里先处理事件，阻止功能需要在 Listener 创建时设置
        handle_mouse_button(button_number)

def start_listener():
    """启动鼠标监听"""
    global listener_thread, is_listening, has_permission
    if not is_mac:
        global _pynput_listener
    
    # 如果已经在运行，重新加载映射（因为配置可能已更新）
    if is_listening:
        load_mappings()  # 重新加载映射
        app_logger.info("监听器已在运行，已重新加载映射", source="mouse_listener")
        return {"success": True, "message": "监听器已在运行，映射已更新"}
    
    # 首先检测权限
    if has_permission is None:
        check_accessibility_permission()
    
    if not has_permission:
        app_logger.warning(f"跳过鼠标监听: {permission_message}", source="mouse_listener")
        return {"success": False, "message": permission_message, "need_permission": True}
    
    load_mappings()
    
    # 即使没有按钮映射也启动监听器，因为用户可能稍后会添加按钮
    # 监听器会正常运行，只是没有映射时不会执行任何操作
    if not button_mappings and not sequence_mappings:
        app_logger.info("当前没有配置按键映射，监听器将启动但不会执行任何操作", source="mouse_listener")
    
    try:
        if is_mac:
            listener_thread = threading.Thread(target=_run_macos_listener, daemon=True)
            listener_thread.start()
            is_listening = True
            app_logger.info("监听器启动中...", source="mouse_listener")
            return {"success": True, "message": "监听器已启动"}
        else:
            _pynput_listener = pynput_mouse.Listener(on_click=_on_click)
            _pynput_listener.start()
            is_listening = True
            app_logger.info("监听器已启动", source="mouse_listener")
            return {"success": True, "message": "监听器已启动"}
    except Exception as e:
        app_logger.error(f"启动监听器失败: {e}", source="mouse_listener")
        is_listening = False
        return {"success": False, "message": f"启动失败: {e}"}

def stop_listener():
    """停止鼠标监听"""
    global is_listening
    
    try:
        # 清理待处理的定时器
        cancel_pending_single_key()
        
        # 清空按键历史
        global key_history
        key_history = []
        
        if is_mac:
            global _run_loop
            if _run_loop:
                CFRunLoopStop(_run_loop)
                _run_loop = None
        else:
            global _pynput_listener
            if _pynput_listener:
                _pynput_listener.stop()
                _pynput_listener = None
    except Exception as e:
        app_logger.error(f"停止监听器时出错: {e}", source="mouse_listener")
    
    is_listening = False
    app_logger.info("监听器已停止", source="mouse_listener")

# API 端点
class ListenerStatus(BaseModel):
    running: bool
    mappings: dict
    sequences: list = []
    message: str
    has_permission: Optional[bool] = None
    permission_message: str = ""

@router.get("/status")
async def get_listener_status():
    """获取监听器状态"""
    return ListenerStatus(
        running=is_listening,
        mappings=button_mappings,
        sequences=[m['sequence'] for m in sequence_mappings],
        message="监听器正在运行" if is_listening else "监听器未运行",
        has_permission=has_permission,
        permission_message=permission_message
    )


def is_listener_running() -> bool:
    """检查监听器是否正在运行"""
    return is_listening

def reload_and_restart_listener():
    """重新加载映射并重启监听器（用于按钮配置变更后）"""
    global is_listening
    
    # 重新加载映射
    load_mappings()
    
    # 如果监听器正在运行，只需要重新加载映射即可（start_listener 会自动处理）
    # 如果监听器未运行，则启动它
    if is_listening:
        # 监听器已在运行，映射已在上面重新加载，直接返回
        app_logger.info("监听器已在运行，映射已更新", source="mouse_listener")
    else:
        # 监听器未运行，启动它
        result = start_listener()
        if result.get("success"):
            app_logger.info("监听器已重新加载映射并启动", source="mouse_listener")
        else:
            app_logger.warning(f"启动监听器失败: {result.get('message')}", source="mouse_listener")

@router.get("/permission")
async def check_permission():
    """检测辅助功能权限"""
    global has_permission
    # 强制重新检测
    has_permission = None
    result = check_accessibility_permission()
    return {
        "has_permission": has_permission,
        "message": permission_message,
        "platform": "macOS" if is_mac else "Windows"
    }

@router.post("/start")
async def start_mouse_listener():
    """启动鼠标监听"""
    try:
        result = start_listener()
        return {
            "status": "success" if result.get("success") else "failed",
            "running": is_listening,
            "mappings": button_mappings,
            "message": result.get("message", ""),
            "has_permission": has_permission,
            "need_permission": result.get("need_permission", False)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_mouse_listener():
    """停止鼠标监听"""
    try:
        stop_listener()
        return {
            "status": "success",
            "running": is_listening,
            "message": "监听器已停止"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reload")
async def reload_mappings_endpoint():
    """重新加载按键映射"""
    try:
        load_mappings()
        return {
            "status": "success",
            "mappings": button_mappings,
            "sequences": [m['sequence'] for m in sequence_mappings],
            "message": f"已加载 {len(button_mappings)} 个单键映射和 {len(sequence_mappings)} 个序列映射"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system-commands")
async def get_system_commands():
    """获取可用的系统命令列表（仅 macOS）"""
    if not is_mac:
        return {
            "status": "success",
            "available": False,
            "message": "系统命令仅在 macOS 上可用",
            "commands": {}
        }
    
    # 返回命令说明（更友好的描述）
    command_descriptions = {
        'launchpad': '启动台',
        'mission_control': '调度中心',
        'mission': '调度中心（简写）',
        'spotlight': 'Spotlight 搜索',
        'siri': 'Siri',
        'finder': 'Finder',
        'desktop': '打开桌面文件夹',
        'downloads': '打开下载文件夹',
        'documents': '打开文稿文件夹',
        'screenshot': '截图（区域选择）',
        'screenshot_area': '截图（区域选择）',
        'screenshot_window': '截图（窗口选择）',
        'screenshot_full': '截图（全屏）',
        'volume_up': '音量增大',
        'volume_down': '音量减小',
        'volume_mute': '静音切换',
        'play_pause': '播放/暂停',
        'next_track': '下一曲',
        'prev_track': '上一曲',
        'lock_screen': '锁定屏幕',
        'sleep': '睡眠',
        'show_desktop': '显示桌面',
    }
    
    return {
        "status": "success",
        "available": True,
        "message": "以下系统命令可直接作为快捷键使用",
        "commands": command_descriptions
    }
