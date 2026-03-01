#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪贴板操作路由
提供复制文本到剪贴板的功能
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import pyperclip

# 创建路由器实例
router = APIRouter()

# 请求模型
class CopyRequest(BaseModel):
    msg: str

# 响应模型
class CopyResponse(BaseModel):
    status: str
    message: str

# 复制文本到剪贴板
@router.post("/copy", response_model=CopyResponse)
async def copy_to_clipboard(request: Request, copy_data: CopyRequest):
    """复制文本到剪贴板"""
    try:
        # 获取要复制的文本
        text = copy_data.msg
        
        if not text:
            raise HTTPException(
                status_code=400,
                detail="No message provided"
            )
        
        # 限制文本长度（防止恶意输入，10MB限制）
        MAX_TEXT_LENGTH = 10 * 1024 * 1024  # 10MB
        if len(text.encode('utf-8')) > MAX_TEXT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Text too long, maximum {MAX_TEXT_LENGTH // 1024 // 1024}MB allowed"
            )
        
        # 复制到剪贴板
        pyperclip.copy(text)
        
        return CopyResponse(
            status="success",
            message="Copied to clipboard"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )



# 获取剪贴板内容（可选功能）
@router.get("/get")
async def get_clipboard_content(request: Request):
    """获取当前剪贴板内容"""
    try:
        # 获取剪贴板内容
        content = pyperclip.paste()
        
        return {
            "status": "success",
            "content": content
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
