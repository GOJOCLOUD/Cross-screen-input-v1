#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端口管理模块
提供端口进程清理功能（Windows专用）

功能：
杀掉占用指定端口的进程
"""

import subprocess

from utils.logger import app_logger


def kill_process_on_port(port: int) -> bool:
    """
    杀掉占用指定端口的进程（Windows专用）
    
    Args:
        port: 要清理的端口号
        
    Returns:
        bool: 成功返回True，失败返回False
    """
    try:
        # Windows: 使用 netstat 和 taskkill
        # 查找占用端口的进程
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            app_logger.warning(f"无法执行 netstat 命令", "port_manager")
            return False
        
        # 查找占用端口的PID
        lines = result.stdout.split('\n')
        pid = None
        for line in lines:
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    break
        
        if pid:
            app_logger.info(f"找到占用端口 {port} 的进程 PID: {pid}", "port_manager")
            # 杀掉进程
            kill_result = subprocess.run(
                ['taskkill', '/F', '/PID', pid],
                capture_output=True,
                text=True,
                timeout=5
            )
            if kill_result.returncode == 0:
                app_logger.info(f"成功杀掉进程 PID: {pid}", "port_manager")
                return True
            else:
                app_logger.warning(f"杀掉进程失败: {kill_result.stderr}", "port_manager")
                return False
        else:
            app_logger.info(f"端口 {port} 未被占用", "port_manager")
            return True
            
    except subprocess.TimeoutExpired:
        app_logger.error("执行命令超时", "port_manager")
        return False
    except Exception as e:
        app_logger.error(f"清理端口 {port} 失败: {e}", "port_manager")
        return False

