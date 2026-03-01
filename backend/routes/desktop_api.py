#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电脑端控制台API
提供电脑端界面所需的数据接口
"""

import os
import socket
import subprocess
import re
from fastapi import APIRouter
from typing import Dict, Any, Optional

from utils.logger import app_logger

router = APIRouter()


def get_local_ip() -> str:
    """获取本机局域网IP地址"""
    try:
        # 使用私有网络地址来获取本地IP，避免使用公共DNS
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.0.0.1", 80))  # 使用私有网络地址
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def get_private_ip() -> Optional[str]:
    """获取私有网络IP地址"""
    try:
        import platform
        system = platform.system()
        private_ips = []
        
        if system == 'Windows':
            # Windows使用ipconfig命令
            result = subprocess.run(['ipconfig'], capture_output=True, text=True)
            # 查找私有网络IP地址
            private_ips = re.findall(r'IPv4 Address[^\d]*(10\.\d+\.\d+\.\d+)', result.stdout)
            private_ips.extend(re.findall(r'IPv4 Address[^\d]*(172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)', result.stdout))
            private_ips.extend(re.findall(r'IPv4 Address[^\d]*(192\.168\.\d+\.\d+)', result.stdout))
            # 如果没有找到，尝试其他格式
            if not private_ips:
                private_ips = re.findall(r'(10\.\d+\.\d+\.\d+)', result.stdout)
                private_ips.extend(re.findall(r'(172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)', result.stdout))
                private_ips.extend(re.findall(r'(192\.168\.\d+\.\d+)', result.stdout))
        else:
            # macOS/Linux使用ifconfig命令
            result = subprocess.run(['ifconfig'], capture_output=True, text=True)
            # 查找私有网络IP地址
            private_ips = re.findall(r'inet\s+(10\.\d+\.\d+\.\d+)', result.stdout)
            private_ips.extend(re.findall(r'inet\s+(172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)', result.stdout))
            private_ips.extend(re.findall(r'inet\s+(192\.168\.\d+\.\d+)', result.stdout))
        
        if private_ips:
            return private_ips[0]  # 返回第一个找到的私有网络IP
        return None
    except Exception as e:
        app_logger.error(f"获取私有网络IP失败: {e}", "desktop_api")
        return None

# 保持向后兼容
def get_hotspot_ip() -> Optional[str]:
    """获取网络IP地址（向后兼容）"""
    return get_private_ip()


def get_server_port() -> int:
    """获取服务器当前端口（固定端口19653）"""
    return 19653


@router.get("/access-info")
async def get_access_info() -> Dict[str, Any]:
    """
    获取访问信息
    
    Returns:
        Dict containing:
        - network_ip: 网络IP地址
        - port: 服务器端口
        - phone_url: 手机端访问URL
        - qrcode_url: 二维码内容URL
    """
    try:
        network_ip = get_hotspot_ip()
        port = get_server_port()
        
        # 构建访问URL - 手机端访问 /phone 路径
        if network_ip:
            phone_url = f"http://{network_ip}:{port}/phone"
            qrcode_url = phone_url
        else:
            # 如果没有网络IP，提示未连接
            phone_url = "未检测到网络连接，请检查网络设置"
            qrcode_url = f"http://localhost:{port}/phone"
        
        app_logger.info(f"返回访问信息: network_ip={network_ip}, port={port}", "desktop_api")
        
        return {
            "network_ip": network_ip,
            "hotspot_ip": network_ip,  # 保持向后兼容
            "port": port,
            "phone_url": phone_url,
            "qrcode_url": qrcode_url,
            "localhost_url": f"http://localhost:{port}"
        }
    except Exception as e:
        app_logger.error(f"获取访问信息失败: {e}", "desktop_api")
        return {
            "network_ip": None,
            "hotspot_ip": None,  # 保持向后兼容
            "port": 19653,
            "phone_url": "http://localhost:19653/phone",
            "qrcode_url": "http://localhost:19653/phone",
            "localhost_url": "http://localhost:19653",
            "error": str(e)
        }


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """
    获取服务状态
    
    Returns:
        Dict containing:
        - server_running: 服务器是否运行
        - port: 服务器端口
        - network_connected: 是否有网络连接
        - mouse_listener_status: 鼠标监听器状态
    """
    try:
        port = get_server_port()
        network_ip = get_hotspot_ip()
        
        # 检查端口是否被占用（服务器是否运行）
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.1)
                result = sock.connect_ex(('localhost', port))
                server_running = result == 0
        except:
            server_running = False
        
        # 检查鼠标监听器状态
        try:
            from routes.mouse_listener import is_listener_running
            mouse_listener_status = is_listener_running()
        except:
            mouse_listener_status = False
        
        app_logger.info(f"返回状态信息: server_running={server_running}, mouse_listener={mouse_listener_status}", "desktop_api")
        
        return {
            "server_running": server_running,
            "port": port,
            "network_connected": network_ip is not None,
            "network_ip": network_ip,
            "hotspot_connected": network_ip is not None,  # 保持向后兼容
            "hotspot_ip": network_ip,  # 保持向后兼容
            "mouse_listener_status": mouse_listener_status,
            "timestamp": app_logger._create_entry("INFO", "", "desktop_api")["timestamp"]
        }
    except Exception as e:
        app_logger.error(f"获取状态信息失败: {e}", "desktop_api")
        return {
            "server_running": False,
            "port": 19653,
            "network_connected": False,
            "network_ip": None,
            "hotspot_connected": False,  # 保持向后兼容
            "hotspot_ip": None,  # 保持向后兼容
            "mouse_listener_status": False,
            "error": str(e)
        }