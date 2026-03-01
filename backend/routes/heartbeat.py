#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
心跳检测API路由
提供连接状态监控和心跳检测功能
"""

import asyncio
import time
from typing import Dict, Set
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

# 导入网络配置管理器
from utils.network_config import network_manager
from utils.logger import info, error

# 创建路由器实例
router = APIRouter()

# 存储活跃连接
active_connections: Dict[str, float] = {}
# 心跳间隔（秒）
HEARTBEAT_INTERVAL = 30

# 请求模型
class HeartbeatRequest(BaseModel):
    device_id: str
    device_name: Optional[str] = None

# 响应模型
class HeartbeatResponse(BaseModel):
    status: str
    timestamp: float
    message: str

class ConnectionStatusResponse(BaseModel):
    active_connections: int
    devices: Dict[str, Dict]

# 心跳检测端点
@router.post("/heartbeat", response_model=HeartbeatResponse)
async def heartbeat(request: Request, data: HeartbeatRequest):
    """接收客户端心跳"""
    try:
        # 获取客户端IP
        client_ip = request.client.host
        
        # 更新活跃连接
        active_connections[data.device_id] = time.time()
        
        # 如果设备已配对，更新最后访问时间
        if network_manager.is_device_paired(data.device_id):
            network_manager.update_device_last_seen(data.device_id)
        
        # 记录心跳
        info(f"收到心跳: {data.device_id} ({client_ip})")
        
        return HeartbeatResponse(
            status="success",
            timestamp=time.time(),
            message="心跳已接收"
        )
    except Exception as e:
        error(f"处理心跳失败: {e}")
        raise HTTPException(status_code=500, detail="处理心跳失败")

# 获取连接状态
@router.get("/status", response_model=ConnectionStatusResponse)
async def get_connection_status():
    """获取当前连接状态"""
    try:
        current_time = time.time()
        
        # 清理过期连接（超过2个心跳间隔）
        expired_devices = []
        for device_id, last_heartbeat in active_connections.items():
            if current_time - last_heartbeat > HEARTBEAT_INTERVAL * 2:
                expired_devices.append(device_id)
        
        for device_id in expired_devices:
            del active_connections[device_id]
            info(f"清理过期连接: {device_id}")
        
        # 构建设备信息
        devices = {}
        for device_id, last_heartbeat in active_connections.items():
            # 检查设备是否已配对
            is_paired = network_manager.is_device_paired(device_id)
            
            # 获取设备信息
            device_info = {
                "last_heartbeat": last_heartbeat,
                "is_paired": is_paired,
                "status": "online" if current_time - last_heartbeat < HEARTBEAT_INTERVAL else "offline"
            }
            
            # 如果设备已配对，添加更多信息
            if is_paired and device_id in network_manager.config.paired_devices:
                paired_info = network_manager.config.paired_devices[device_id]
                device_info["name"] = paired_info.get("name", "未知设备")
                device_info["paired_at"] = paired_info.get("paired_at")
            
            devices[device_id] = device_info
        
        return ConnectionStatusResponse(
            active_connections=len(active_connections),
            devices=devices
        )
    except Exception as e:
        error(f"获取连接状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取连接状态失败")

# 启动心跳监控任务
async def start_heartbeat_monitor():
    """启动心跳监控任务"""
    while True:
        try:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            
            current_time = time.time()
            expired_devices = []
            
            # 检查过期连接
            for device_id, last_heartbeat in active_connections.items():
                if current_time - last_heartbeat > HEARTBEAT_INTERVAL * 2:
                    expired_devices.append(device_id)
            
            # 清理过期连接
            for device_id in expired_devices:
                del active_connections[device_id]
                info(f"设备离线: {device_id}")
                
        except Exception as e:
            error(f"心跳监控错误: {e}")
            await asyncio.sleep(5)  # 出错后短暂等待

# 启动心跳监控
@app.on_event("startup")
async def startup_heartbeat_monitor():
    """应用启动时启动心跳监控"""
    asyncio.create_task(start_heartbeat_monitor())
    info("心跳监控已启动")

# 获取心跳配置
@router.get("/config")
async def get_heartbeat_config():
    """获取心跳配置"""
    return {
        "interval": HEARTBEAT_INTERVAL,
        "timeout": HEARTBEAT_INTERVAL * 2,
        "message": "客户端应每30秒发送一次心跳"
    }