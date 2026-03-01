#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鼠标按钮配置管理路由
提供鼠标按钮配置的增删改查API
"""

# 标准库
import sys
import os
import re
import json
from datetime import datetime
from typing import List, Optional

# 第三方库
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator, Field

# 添加utils目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入配置
from config import DATA_DIR

router = APIRouter()

# 数据文件路径（使用统一的配置）
JSON_FILE = os.path.join(DATA_DIR, "mouse_buttons.json")

def ensure_data_dir():
    """确保数据目录存在"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def load_buttons_data() -> dict:
    """从JSON文件加载数据"""
    ensure_data_dir()
    
    default_data = {
        "buttons": [],
        "version": "1.0",
        "last_updated": None
    }
    
    try:
        if not os.path.exists(JSON_FILE):
            # 文件不存在，直接创建并返回默认数据
            with open(JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)
            return default_data
        
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"加载鼠标按钮配置失败: {e}")
        return default_data

def save_buttons_data(data: dict) -> bool:
    """保存数据到JSON文件"""
    ensure_data_dir()
    
    try:
        data["last_updated"] = datetime.now().isoformat()
        
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存鼠标按钮配置失败: {e}")
        return False

def load_buttons() -> List[dict]:
    """获取所有鼠标按钮列表"""
    data = load_buttons_data()
    return data.get("buttons", [])

def save_buttons(buttons: List[dict]) -> bool:
    """保存鼠标按钮列表"""
    data = load_buttons_data()
    data["buttons"] = buttons
    return save_buttons_data(data)

def get_button_by_id(button_id: str) -> Optional[dict]:
    """根据ID获取鼠标按钮"""
    buttons = load_buttons()
    for button in buttons:
        if button.get("id") == button_id:
            return button
    return None

def add_button(button_data: dict) -> dict:
    """添加新鼠标按钮"""
    buttons = load_buttons()
    
    # 确保有ID
    if "id" not in button_data:
        button_data["id"] = f"mouse_{int(datetime.now().timestamp() * 1000)}_{hash(button_data.get('name', '')) % 10000}"
    
    # 添加时间戳
    now = datetime.now().isoformat()
    button_data["created_at"] = now
    button_data["updated_at"] = now
    
    # 确保有order字段
    if "order" not in button_data:
        button_data["order"] = int(datetime.now().timestamp() * 1000)
    
    buttons.append(button_data)
    save_buttons(buttons)
    
    return button_data

def update_button(button_id: str, button_data: dict) -> Optional[dict]:
    """更新鼠标按钮"""
    buttons = load_buttons()
    
    for i, button in enumerate(buttons):
        if button.get("id") == button_id:
            updated_button = {**button, **button_data}
            updated_button["updated_at"] = datetime.now().isoformat()
            updated_button["id"] = button_id  # 确保ID不变
            
            buttons[i] = updated_button
            save_buttons(buttons)
            
            return updated_button
    
    return None

def delete_button(button_id: str) -> bool:
    """删除鼠标按钮"""
    buttons = load_buttons()
    original_count = len(buttons)
    
    buttons = [b for b in buttons if b.get("id") != button_id]
    
    if len(buttons) < original_count:
        save_buttons(buttons)
        return True
    
    return False

# 有效的鼠标按键类型
VALID_KEY_TYPES = ['left', 'right', 'middle', 'side1', 'side2']

def validate_sequence(sequence: List[str]) -> bool:
    """验证按键序列是否有效"""
    if not sequence or len(sequence) == 0:
        return False
    for key in sequence:
        if key not in VALID_KEY_TYPES:
            return False
    return True

# 请求模型
class MouseButtonConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=20, description="按钮名称")
    action: str = Field(..., description="映射的快捷键，如 ctrl+v")
    keyType: Optional[str] = Field(default=None, description="鼠标按键类型（单键模式）：left, right, middle, side1, side2")
    sequence: Optional[List[str]] = Field(default=None, description="按键序列（序列模式）：如 ['side1', 'side2']")
    icon: Optional[str] = Field(default=None, max_length=10, description="按钮图标（可选）")
    order: Optional[int] = Field(default=None, ge=0, description="排序顺序")
    
    @validator('action')
    def validate_action(cls, v):
        # 转换为小写格式
        v = v.strip().lower()
        # 验证快捷键格式：ctrl+v 或系统命令如 launchpad, mission_control 等
        pattern = r'^[a-z0-9_]+(\+[a-z0-9_]+)*$'
        if not re.match(pattern, v):
            raise ValueError('快捷键格式不正确，必须使用小写字母、数字和下划线，用+分隔，例如：ctrl+v 或 launchpad')
        return v
    
    @validator('keyType')
    def validate_key_type(cls, v):
        if v:
            if v not in VALID_KEY_TYPES:
                raise ValueError(f'鼠标按键类型必须是：{", ".join(VALID_KEY_TYPES)}')
        return v
    
    @validator('sequence')
    def validate_sequence_field(cls, v):
        if v:
            if not validate_sequence(v):
                raise ValueError(f'按键序列中的每个按键必须是：{", ".join(VALID_KEY_TYPES)}')
        return v
    
    @validator('sequence', always=True)
    def validate_key_or_sequence(cls, v, values):
        key_type = values.get('keyType')
        # 必须提供 keyType 或 sequence 其中之一
        if not key_type and not v:
            raise ValueError('必须提供 keyType（单键模式）或 sequence（序列模式）')
        return v

class MouseButtonUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=20, description="按钮名称")
    action: Optional[str] = Field(default=None, description="映射的快捷键，如 ctrl+v")
    keyType: Optional[str] = Field(default=None, description="鼠标按键类型（单键模式）：left, right, middle, side1, side2")
    sequence: Optional[List[str]] = Field(default=None, description="按键序列（序列模式）：如 ['side1', 'side2']")
    icon: Optional[str] = Field(default=None, max_length=10, description="按钮图标（可选）")
    order: Optional[int] = Field(default=None, ge=0, description="排序顺序")
    
    @validator('action')
    def validate_action(cls, v):
        if v:
            # 转换为小写格式
            v = v.strip().lower()
            # 验证快捷键格式：ctrl+v 或系统命令如 launchpad, mission_control 等
            pattern = r'^[a-z0-9_]+(\+[a-z0-9_]+)*$'
            if not re.match(pattern, v):
                raise ValueError('快捷键格式不正确，必须使用小写字母、数字和下划线，用+分隔，例如：ctrl+v 或 launchpad')
        return v
    
    @validator('keyType')
    def validate_key_type(cls, v):
        if v:
            if v not in VALID_KEY_TYPES:
                raise ValueError(f'鼠标按键类型必须是：{", ".join(VALID_KEY_TYPES)}')
        return v
    
    @validator('sequence')
    def validate_sequence_field(cls, v):
        if v:
            if not validate_sequence(v):
                raise ValueError(f'按键序列中的每个按键必须是：{", ".join(VALID_KEY_TYPES)}')
        return v

# 响应模型
class MouseButtonListResponse(BaseModel):
    status: str
    buttons: List[dict]
    count: int

class MouseButtonResponse(BaseModel):
    status: str
    button: dict
    message: str

# API端点
@router.get("/list", response_model=MouseButtonListResponse)
async def get_mouse_button_list():
    """获取所有鼠标按钮列表"""
    try:
        buttons = load_buttons()
        return MouseButtonListResponse(
            status="success",
            buttons=buttons,
            count=len(buttons)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取鼠标按钮列表失败: {str(e)}"
        )

@router.post("/add", response_model=MouseButtonResponse)
async def add_mouse_button_config(button: MouseButtonConfig):
    """添加新鼠标按钮"""
    try:
        button_data = button.dict(exclude_none=True)
        new_button = add_button(button_data)
        
        # 重新加载映射并重启监听器
        try:
            from routes.mouse_listener import reload_and_restart_listener
            reload_and_restart_listener()
        except Exception as e:
            # 如果重启监听器失败，不影响按钮添加的成功返回
            import logging
            logging.warning(f"重启监听器失败: {e}")
        
        return MouseButtonResponse(
            status="success",
            button=new_button,
            message="鼠标按钮添加成功"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"添加鼠标按钮失败: {str(e)}"
        )

@router.put("/update/{button_id}", response_model=MouseButtonResponse)
async def update_mouse_button_config(button_id: str, button: MouseButtonUpdate):
    """更新鼠标按钮"""
    try:
        # 检查按钮是否存在
        existing_button = get_button_by_id(button_id)
        if not existing_button:
            raise HTTPException(
                status_code=404,
                detail="鼠标按钮不存在"
            )
        
        # 更新按钮
        button_data = button.dict(exclude_none=True)
        updated_button = update_button(button_id, button_data)
        
        if not updated_button:
            raise HTTPException(
                status_code=500,
                detail="更新鼠标按钮失败"
            )
        
        # 重新加载映射并重启监听器
        try:
            from routes.mouse_listener import reload_and_restart_listener
            reload_and_restart_listener()
        except Exception as e:
            # 如果重启监听器失败，不影响按钮更新的成功返回
            import logging
            logging.warning(f"重启监听器失败: {e}")
        
        return MouseButtonResponse(
            status="success",
            button=updated_button,
            message="鼠标按钮更新成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"更新鼠标按钮失败: {str(e)}"
        )

@router.delete("/delete/{button_id}")
async def delete_mouse_button_config(button_id: str):
    """删除鼠标按钮"""
    try:
        # 检查按钮是否存在
        existing_button = get_button_by_id(button_id)
        if not existing_button:
            raise HTTPException(
                status_code=404,
                detail="鼠标按钮不存在"
            )
        
        # 删除按钮
        success = delete_button(button_id)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="删除鼠标按钮失败"
            )
        
        # 重新加载映射并重启监听器（即使没有按钮了也要保持监听器运行）
        try:
            from routes.mouse_listener import reload_and_restart_listener
            reload_and_restart_listener()
        except Exception as e:
            # 如果重启监听器失败，不影响按钮删除的成功返回
            import logging
            logging.warning(f"重启监听器失败: {e}")
        
        return {
            "status": "success",
            "message": "鼠标按钮删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"删除鼠标按钮失败: {str(e)}"
        )

@router.get("/get/{button_id}", response_model=MouseButtonResponse)
async def get_mouse_button_config(button_id: str):
    """获取单个鼠标按钮"""
    try:
        button = get_button_by_id(button_id)
        
        if not button:
            raise HTTPException(
                status_code=404,
                detail="鼠标按钮不存在"
            )
        
        return MouseButtonResponse(
            status="success",
            button=button,
            message="获取鼠标按钮成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取鼠标按钮失败: {str(e)}"
        )