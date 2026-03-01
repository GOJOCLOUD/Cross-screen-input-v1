#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按钮配置管理路由
提供按钮配置的增删改查API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator, Field
from typing import List, Optional
import sys
import os
import re

# 添加utils目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.shortcut_storage import (
    load_buttons,
    add_button,
    update_button,
    delete_button,
    get_button_by_id
)

router = APIRouter()

# 请求模型
class ButtonConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=20, description="按钮名称")
    icon: Optional[str] = Field(default="🔘", max_length=10, description="按钮图标")
    type: str = Field(..., description="操作类型")
    shortcut: Optional[str] = Field(default=None, description="快捷键（单次点击）")
    multiActions: Optional[List[dict]] = Field(default=None, description="多次点击动作")
    toggleActions: Optional[dict] = Field(default=None, description="激活模式动作")
    autoCloseDuration: Optional[int] = Field(default=None, ge=0, description="自动关闭时长（秒），0或None表示不自动关闭，仅用于toggle类型")
    order: Optional[int] = Field(default=None, ge=0, description="排序顺序")
    
    @validator('type')
    def validate_type(cls, v):
        if v not in ['single', 'multi', 'toggle']:
            raise ValueError('操作类型必须是 single、multi 或 toggle')
        return v
    
    @validator('shortcut')
    def validate_shortcut(cls, v, values):
        if values.get('type') == 'single' and not v:
            raise ValueError('单次点击类型必须提供快捷键')
        if v:
            # 转换为小写格式
            v = v.strip().lower()
            # 验证快捷键格式：ctrl+v, alt+tab, ctrl+up 等（小写格式，支持下划线）
            pattern = r'^[a-z0-9_]+(\+[a-z0-9_]+)*$'
            if not re.match(pattern, v):
                raise ValueError('快捷键格式不正确，必须使用小写字母、数字和下划线，用+分隔，例如：ctrl+v, ctrl+up')
        return v
    
    @validator('multiActions')
    def validate_multi_actions(cls, v, values):
        if values.get('type') == 'multi':
            if not v or len(v) == 0:
                raise ValueError('多次点击类型必须提供至少一个动作')
            for action in v:
                if not action.get('shortcut'):
                    raise ValueError('每个多次点击动作必须提供快捷键')
        return v
    
    @validator('toggleActions')
    def validate_toggle_actions(cls, v, values):
        if values.get('type') == 'toggle':
            if not v:
                raise ValueError('激活模式必须提供动作配置')
            if not v.get('activate') or not v.get('deactivate'):
                raise ValueError('激活模式必须提供激活和取消激活的快捷键')
        return v
    
    @validator('autoCloseDuration')
    def validate_auto_close_duration(cls, v, values):
        # 只有toggle类型才需要自动关闭时长
        if values.get('type') == 'toggle' and v is not None:
            if v < 0:
                raise ValueError('自动关闭时长不能为负数')
        # 非toggle类型不应该有自动关闭时长
        elif values.get('type') != 'toggle' and v is not None:
            raise ValueError('只有toggle类型按钮才能设置自动关闭时长')
        return v

class ButtonUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=20, description="按钮名称")
    icon: Optional[str] = Field(default=None, max_length=10, description="按钮图标")
    type: Optional[str] = Field(default=None, description="操作类型")
    shortcut: Optional[str] = Field(default=None, description="快捷键（单次点击）")
    multiActions: Optional[List[dict]] = Field(default=None, description="多次点击动作")
    toggleActions: Optional[dict] = Field(default=None, description="激活模式动作")
    autoCloseDuration: Optional[int] = Field(default=None, ge=0, description="自动关闭时长（秒），0或None表示不自动关闭")
    order: Optional[int] = Field(default=None, ge=0, description="排序顺序")
    
    @validator('type')
    def validate_type(cls, v):
        if v and v not in ['single', 'multi', 'toggle']:
            raise ValueError('操作类型必须是 single、multi 或 toggle')
        return v
    
    @validator('shortcut')
    def validate_shortcut(cls, v):
        if v:
            # 转换为小写格式
            v = v.strip().lower()
            # 验证快捷键格式：ctrl+v, alt+tab, ctrl+up 等（小写格式，支持下划线）
            pattern = r'^[a-z0-9_]+(\+[a-z0-9_]+)*$'
            if not re.match(pattern, v):
                raise ValueError('快捷键格式不正确，必须使用小写字母、数字和下划线，用+分隔，例如：ctrl+v, ctrl+up')
        return v
    
    @validator('autoCloseDuration')
    def validate_auto_close_duration(cls, v, values):
        # 如果提供了type，检查类型
        button_type = values.get('type')
        if button_type == 'toggle' and v is not None:
            if v < 0:
                raise ValueError('自动关闭时长不能为负数')
        elif button_type and button_type != 'toggle' and v is not None:
            raise ValueError('只有toggle类型按钮才能设置自动关闭时长')
        return v

# 响应模型
class ButtonListResponse(BaseModel):
    status: str
    buttons: List[dict]
    count: int

class ButtonResponse(BaseModel):
    status: str
    button: dict
    message: str

# API端点
@router.get("/list", response_model=ButtonListResponse)
async def get_button_list():
    """获取所有按钮列表"""
    try:
        buttons = load_buttons()
        return ButtonListResponse(
            status="success",
            buttons=buttons,
            count=len(buttons)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取按钮列表失败: {str(e)}"
        )

@router.post("/add", response_model=ButtonResponse)
async def add_button_config(button: ButtonConfig):
    """添加新按钮"""
    try:
        button_data = button.dict(exclude_none=True)
        
        # 根据类型清理不需要的字段
        button_type = button_data.get("type")
        if button_type == 'single':
            button_data.pop('multiActions', None)
            button_data.pop('toggleActions', None)
        elif button_type == 'multi':
            button_data.pop('shortcut', None)
            button_data.pop('toggleActions', None)
        elif button_type == 'toggle':
            button_data.pop('shortcut', None)
            button_data.pop('multiActions', None)
        
        new_button = add_button(button_data)
        
        return ButtonResponse(
            status="success",
            button=new_button,
            message="按钮添加成功"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"添加按钮失败: {str(e)}"
        )

@router.put("/update/{button_id}", response_model=ButtonResponse)
async def update_button_config(button_id: str, button: ButtonUpdate):
    """更新按钮"""
    try:
        # 检查按钮是否存在
        existing_button = get_button_by_id(button_id)
        if not existing_button:
            raise HTTPException(
                status_code=404,
                detail="按钮不存在"
            )
        
        # 更新按钮
        button_data = button.dict(exclude_none=True)
        
        # 确定新的类型（如果提供了type则使用新的，否则使用原有的）
        new_type = button_data.get("type", existing_button.get("type"))
        
        # 根据类型清理不需要的字段
        if new_type == 'single':
            button_data.pop('multiActions', None)
            button_data.pop('toggleActions', None)
        elif new_type == 'multi':
            button_data.pop('shortcut', None)
            button_data.pop('toggleActions', None)
        elif new_type == 'toggle':
            button_data.pop('shortcut', None)
            button_data.pop('multiActions', None)
        
        updated_button = update_button(button_id, button_data)
        
        if not updated_button:
            raise HTTPException(
                status_code=500,
                detail="更新按钮失败"
            )
        
        return ButtonResponse(
            status="success",
            button=updated_button,
            message="按钮更新成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"更新按钮失败: {str(e)}"
        )

@router.delete("/delete/{button_id}")
async def delete_button_config(button_id: str):
    """删除按钮"""
    try:
        # 检查按钮是否存在
        existing_button = get_button_by_id(button_id)
        if not existing_button:
            raise HTTPException(
                status_code=404,
                detail="按钮不存在"
            )
        
        # 删除按钮
        success = delete_button(button_id)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="删除按钮失败"
            )
        
        return {
            "status": "success",
            "message": "按钮删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"删除按钮失败: {str(e)}"
        )

@router.get("/get/{button_id}", response_model=ButtonResponse)
async def get_button_config(button_id: str):
    """获取单个按钮"""
    try:
        button = get_button_by_id(button_id)
        
        if not button:
            raise HTTPException(
                status_code=404,
                detail="按钮不存在"
            )
        
        return ButtonResponse(
            status="success",
            button=button,
            message="获取按钮成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取按钮失败: {str(e)}"
        )
