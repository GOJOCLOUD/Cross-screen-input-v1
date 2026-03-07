#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监听API路由
提供剪贴板变化监听功能
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, AsyncGenerator, Dict
import asyncio
import json
import traceback
import sys
import os

# 添加utils目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.clipboard_monitor import clipboard_monitor
from utils.logger import info, error

router = APIRouter()

# 存储每个按钮的事件队列
button_events: Dict[str, asyncio.Queue] = {}
# 存储主事件循环的引用
main_event_loop: Optional[asyncio.AbstractEventLoop] = None

class MonitorRequest(BaseModel):
    button_id: str
    action: str  # "start" or "stop"

class MonitorResponse(BaseModel):
    status: str
    message: str
    button_id: str
    is_monitoring: bool

def on_clipboard_change(button_id: str) -> None:
    """剪贴板变化回调（从轮询线程调用）"""
    info(f"🔔 剪贴板变化回调触发: {button_id}", source="monitor_api")
    
    # 将事件放入队列
    if button_id not in button_events:
        error(f"按钮 {button_id} 的事件队列不存在", source="monitor_api")
        return
    
    try:
        event_data = {"type": "clipboard_change", "button_id": button_id}
        queue = button_events[button_id]
        
        # 使用线程安全的方式添加事件
        if main_event_loop and main_event_loop.is_running():
            info("使用 run_coroutine_threadsafe 发送事件", source="monitor_api")
            future = asyncio.run_coroutine_threadsafe(
                queue.put(event_data),
                main_event_loop
            )
            # 等待完成（最多1秒）
            try:
                future.result(timeout=1)
                info("✅ 事件已放入队列", source="monitor_api")
            except Exception as e:
                error(f"等待事件放入队列超时: {e}", source="monitor_api")
        else:
            info("事件循环未运行，使用 put_nowait", source="monitor_api")
            queue.put_nowait(event_data)
            info("✅ 事件已放入队列 (put_nowait)", source="monitor_api")
            
    except Exception as e:
        error(f"发送事件失败: {e}", source="monitor_api")
        error(f"详细错误: {traceback.format_exc()}", source="monitor_api")

@router.post("/control", response_model=MonitorResponse)
async def control_monitor(request: MonitorRequest) -> MonitorResponse:
    """控制剪贴板监听"""
    global main_event_loop
    
    # 保存当前事件循环的引用
    try:
        main_event_loop = asyncio.get_running_loop()
        info("已保存主事件循环引用", source="monitor_api")
    except RuntimeError:
        pass
    
    button_id = request.button_id
    action = request.action
    
    info(f"监听控制请求: button_id={button_id}, action={action}", source="monitor_api")
    
    if action == "start":
        # 创建事件队列
        if button_id not in button_events:
            button_events[button_id] = asyncio.Queue()
        
        # 开始监听
        clipboard_monitor.start_monitoring(button_id, on_clipboard_change)
        
        return MonitorResponse(
            status="success",
            message="监听已启动",
            button_id=button_id,
            is_monitoring=True
        )
    
    elif action == "stop":
        # 停止监听
        clipboard_monitor.stop_monitoring(button_id)
        
        # 清理事件队列
        if button_id in button_events:
            del button_events[button_id]
        
        return MonitorResponse(
            status="success",
            message="监听已停止",
            button_id=button_id,
            is_monitoring=False
        )
    
    else:
        raise HTTPException(status_code=400, detail=f"未知操作: {action}")

@router.get("/status/{button_id}")
async def get_monitor_status(button_id: str) -> dict:
    """获取监听状态"""
    is_monitoring = clipboard_monitor.is_monitoring(button_id)
    return {
        "status": "success",
        "button_id": button_id,
        "is_monitoring": is_monitoring
    }


@router.get("/active")
async def get_active_monitors() -> dict:
    """获取所有活动的监听"""
    monitors = clipboard_monitor.get_active_monitors()
    return {
        "status": "success",
        "monitors": monitors,
        "count": len(monitors)
    }


@router.get("/events/{button_id}")
async def get_events(button_id: str) -> StreamingResponse:
    """SSE端点：获取指定按钮的事件流"""
    
    async def event_generator() -> AsyncGenerator[str, None]:
        info(f"SSE连接建立: {button_id}", source="monitor_api")
        
        # 确保队列存在
        if button_id not in button_events:
            button_events[button_id] = asyncio.Queue()
        
        queue = button_events[button_id]
        
        # 发送连接确认
        yield f"data: {json.dumps({'type': 'connected', 'button_id': button_id})}\n\n"
        
        try:
            while True:
                try:
                    # 等待事件，超时30秒发送心跳
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    info(f"发送SSE事件: {event}", source="monitor_api")
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # 发送心跳
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        except asyncio.CancelledError:
            info(f"SSE连接关闭: {button_id}", source="monitor_api")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
