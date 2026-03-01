#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件
管理项目路径和其他配置
Windows专用版本，支持 Electron 打包后的路径检测
"""

import os
import sys
import shutil


def is_packaged():
    """检测是否在打包环境中运行（PyInstaller 或 Electron）"""
    # PyInstaller 打包后会设置 frozen 属性
    if getattr(sys, 'frozen', False):
        return True
    # 检查环境变量（由 Electron 主进程设置）
    if os.environ.get('ELECTRON_RUN_AS_NODE') or os.environ.get('KPSR_PACKAGED'):
        return True
    return False


def get_base_path():
    """获取基础路径（资源文件位置）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，_MEIPASS 是临时解压目录
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_executable_dir():
    """获取可执行文件所在目录（用于找到 frontend 等资源）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，可执行文件所在目录
        # 目录模式：kpsr-backend 在 Resources/kpsr-backend/ 下
        # frontend 在 Resources/frontend/ 下
        # 所以需要返回父目录 (Resources/)
        exe_dir = os.path.dirname(sys.executable)
        # 如果是在 kpsr-backend 子目录中，返回父目录
        if os.path.basename(exe_dir) == 'kpsr-backend':
            return os.path.dirname(exe_dir)
        return exe_dir
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_user_data_dir():
    """获取用户数据目录（Windows专用）"""
    # Windows: %APPDATA%/KPSR
    return os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'KPSR')


# 判断运行环境
IS_PACKAGED = is_packaged()

# 获取项目根目录（源码位置）
if IS_PACKAGED:
    # 打包后：可执行文件所在目录就是资源目录
    PROJECT_ROOT = get_executable_dir()
else:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 获取前端目录路径
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

if IS_PACKAGED:
    # 打包环境：使用用户数据目录
    USER_DATA_DIR = get_user_data_dir()
    DATA_DIR = os.path.join(USER_DATA_DIR, "data")
    LOGS_DIR = os.path.join(USER_DATA_DIR, "logs")
    
    # 内嵌的默认数据目录（PyInstaller 打包时会解压到 _MEIPASS）
    BASE_PATH = get_base_path()
    BUNDLED_DATA_DIR = os.path.join(BASE_PATH, "data")
else:
    # 开发环境：使用项目目录
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
    BUNDLED_DATA_DIR = None
    BASE_PATH = PROJECT_ROOT

# 确保目录存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)


def init_default_data():
    """
    初始化默认配置文件
    打包后首次运行时，将内嵌的默认配置复制到用户数据目录
    """
    if not IS_PACKAGED or not BUNDLED_DATA_DIR:
        return
    
    if not os.path.exists(BUNDLED_DATA_DIR):
        return
    
    # 首次运行标记文件（使用版本号）
    APP_VERSION = "1.0.0"
    first_run_marker = os.path.join(DATA_DIR, f'.kpsr_initialized_v{APP_VERSION}')
    
    # 检查是否是首次运行
    is_first_run = not os.path.exists(first_run_marker)
    
    if is_first_run:
        print("[KPSR] ========================================")
        print("[KPSR] 检测到首次运行，初始化默认配置...")
        print(f"[KPSR] 数据目录: {DATA_DIR}")
        print(f"[KPSR] 首次运行标记: {first_run_marker}")
        
        # 确保目录存在
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # 创建首次运行标记文件
        try:
            with open(first_run_marker, 'w', encoding='utf-8') as f:
                f.write('initialized')
            print("[KPSR] ✅ 已创建首次运行标记")
        except Exception as e:
            print(f"[KPSR] ⚠️ 创建首次运行标记失败: {e}")
        
        print("[KPSR] ========================================")
    
    # 排除的文件列表
    excluded_files = []
    
    # 复制默认配置文件（如果目标不存在）
    for filename in os.listdir(BUNDLED_DATA_DIR):
        # 跳过排除的文件
        if filename in excluded_files:
            continue
            
        src = os.path.join(BUNDLED_DATA_DIR, filename)
        dst = os.path.join(DATA_DIR, filename)
        
        # 只在目标文件不存在时复制（保护用户已有配置）
        if os.path.isfile(src) and not os.path.exists(dst):
            try:
                shutil.copy2(src, dst)
                print(f"[KPSR] 已初始化默认配置: {filename}")
            except Exception as e:
                print(f"[KPSR] 复制配置失败 {filename}: {e}")


# 初始化默认数据
init_default_data()

print(f"[KPSR] 运行模式: {'打包环境' if IS_PACKAGED else '开发环境'}")
print(f"[KPSR] 数据目录: {DATA_DIR}")
print(f"[KPSR] 日志目录: {LOGS_DIR}")

__all__ = ['PROJECT_ROOT', 'FRONTEND_DIR', 'DATA_DIR', 'LOGS_DIR', 'IS_PACKAGED']
