#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志API路由
提供日志记录、查询和管理功能
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import sys
import os

# 添加utils目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import app_logger, log_frontend, get_logs, clear_logs, get_log_stats

router = APIRouter()

# 请求模型
class FrontendLogRequest(BaseModel):
    level: str
    message: str
    extra: Optional[dict] = None

class BatchLogRequest(BaseModel):
    logs: List[FrontendLogRequest]

# 响应模型
class LogEntry(BaseModel):
    timestamp: str
    level: str
    source: str
    message: str
    extra: Optional[dict] = None

class LogsResponse(BaseModel):
    status: str
    logs: List[dict]
    count: int

class LogStatsResponse(BaseModel):
    status: str
    stats: dict

# API端点

@router.post("/frontend")
async def log_from_frontend(request: FrontendLogRequest):
    """接收前端日志"""
    try:
        log_frontend(request.level, request.message, request.extra)
        return {"status": "success", "message": "日志已记录"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录日志失败: {str(e)}")

@router.post("/frontend/batch")
async def log_batch_from_frontend(request: BatchLogRequest):
    """批量接收前端日志"""
    try:
        for log in request.logs:
            log_frontend(log.level, log.message, log.extra)
        return {"status": "success", "message": f"已记录 {len(request.logs)} 条日志"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录日志失败: {str(e)}")

@router.get("/list", response_model=LogsResponse)
async def get_log_list(
    limit: int = Query(100, ge=1, le=10000, description="返回的日志条数"),
    level: Optional[str] = Query(None, description="日志级别过滤 (DEBUG/INFO/WARNING/ERROR)"),
    source: Optional[str] = Query(None, description="来源过滤 (frontend/backend)"),
    start_time: Optional[str] = Query(None, description="开始时间 (ISO格式)"),
    end_time: Optional[str] = Query(None, description="结束时间 (ISO格式)")
):
    """获取日志列表"""
    try:
        logs = get_logs(
            limit=limit,
            level=level,
            source=source,
            start_time=start_time,
            end_time=end_time
        )
        return LogsResponse(
            status="success",
            logs=logs,
            count=len(logs)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")

@router.get("/stats", response_model=LogStatsResponse)
async def get_statistics():
    """获取日志统计"""
    try:
        stats = get_log_stats()
        return LogStatsResponse(
            status="success",
            stats=stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")

@router.delete("/clear")
async def clear_all_logs():
    """清空所有日志"""
    try:
        success = clear_logs()
        if success:
            return {"status": "success", "message": "日志已清空"}
        else:
            raise HTTPException(status_code=500, detail="清空日志失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空日志失败: {str(e)}")

@router.get("/recent")
async def get_recent_logs(count: int = Query(50, ge=1, le=500)):
    """获取最近的日志（简化接口）"""
    try:
        logs = get_logs(limit=count)
        return {
            "status": "success",
            "logs": logs,
            "count": len(logs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")

@router.get("/errors")
async def get_error_logs(count: int = Query(50, ge=1, le=500)):
    """获取错误日志"""
    try:
        logs = get_logs(limit=count, level="ERROR")
        return {
            "status": "success",
            "logs": logs,
            "count": len(logs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")

@router.get("/frontend-logs")
async def get_frontend_only_logs(count: int = Query(100, ge=1, le=1000)):
    """只获取前端日志"""
    try:
        logs = get_logs(limit=count, source="frontend")
        return {
            "status": "success",
            "logs": logs,
            "count": len(logs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")

@router.get("/backend-logs")
async def get_backend_only_logs(count: int = Query(100, ge=1, le=1000)):
    """只获取后端日志"""
    try:
        logs = get_logs(limit=count, source="backend")
        return {
            "status": "success",
            "logs": logs,
            "count": len(logs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")
