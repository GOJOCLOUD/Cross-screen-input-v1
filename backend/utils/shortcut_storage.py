#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快捷键按钮配置存储管理
提供JSON文件的增删改查功能
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Optional

# 添加父目录到路径以导入 config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_DIR

# 数据文件路径（使用统一的配置）
JSON_FILE = os.path.join(DATA_DIR, "shortcut_buttons.json")

def ensure_data_dir():
    """确保数据目录存在"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    # 如果JSON文件不存在，创建初始文件
    if not os.path.exists(JSON_FILE):
        initial_data = {
            "buttons": [],
            "version": "1.0",
            "last_updated": None
        }
        save_buttons_data(initial_data)

def load_buttons_data() -> Dict:
    """从JSON文件加载数据"""
    ensure_data_dir()
    
    try:
        if not os.path.exists(JSON_FILE):
            return {
                "buttons": [],
                "version": "1.0",
                "last_updated": None
            }
        
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"加载按钮配置失败: {e}")
        return {
            "buttons": [],
            "version": "1.0",
            "last_updated": None
        }

def save_buttons_data(data: Dict):
    """保存数据到JSON文件"""
    ensure_data_dir()
    
    try:
        data["last_updated"] = datetime.now().isoformat()
        
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存按钮配置失败: {e}")
        return False

def load_buttons() -> List[Dict]:
    """获取所有按钮列表"""
    data = load_buttons_data()
    return data.get("buttons", [])

def save_buttons(buttons: List[Dict]) -> bool:
    """保存按钮列表"""
    data = load_buttons_data()
    data["buttons"] = buttons
    return save_buttons_data(data)

def get_button_by_id(button_id: str) -> Optional[Dict]:
    """根据ID获取按钮"""
    buttons = load_buttons()
    for button in buttons:
        if button.get("id") == button_id:
            return button
    return None

def add_button(button_data: Dict) -> Dict:
    """添加新按钮"""
    buttons = load_buttons()
    
    # 确保有ID
    if "id" not in button_data:
        button_data["id"] = f"btn_{int(datetime.now().timestamp() * 1000)}_{hash(button_data.get('name', '')) % 10000}"
    
    # 添加时间戳
    now = datetime.now().isoformat()
    button_data["created_at"] = now
    button_data["updated_at"] = now
    
    # 确保有order字段
    if "order" not in button_data:
        button_data["order"] = int(datetime.now().timestamp() * 1000)
    
    # 根据类型清理不需要的字段
    button_type = button_data.get("type")
    if button_type == 'single':
        # 单次点击：只保留 shortcut
        button_data.pop('multiActions', None)
        button_data.pop('toggleActions', None)
    elif button_type == 'multi':
        # 多次点击：只保留 multiActions
        button_data.pop('shortcut', None)
        button_data.pop('toggleActions', None)
    elif button_type == 'toggle':
        # 激活模式：只保留 toggleActions
        button_data.pop('shortcut', None)
        button_data.pop('multiActions', None)
    
    buttons.append(button_data)
    save_buttons(buttons)
    
    return button_data

def update_button(button_id: str, button_data: Dict) -> Optional[Dict]:
    """更新按钮"""
    buttons = load_buttons()
    
    for i, button in enumerate(buttons):
        if button.get("id") == button_id:
            # 获取新的类型
            new_type = button_data.get("type", button.get("type"))
            
            # 保留原有字段，但根据新类型清理不需要的字段
            updated_button = {**button, **button_data}
            updated_button["updated_at"] = datetime.now().isoformat()
            updated_button["id"] = button_id  # 确保ID不变
            
            # 根据类型清理不需要的字段
            if new_type == 'single':
                # 单次点击：只保留 shortcut，删除 multiActions 和 toggleActions
                updated_button.pop('multiActions', None)
                updated_button.pop('toggleActions', None)
                # 确保有 shortcut 字段
                if 'shortcut' not in updated_button:
                    updated_button['shortcut'] = None
            elif new_type == 'multi':
                # 多次点击：只保留 multiActions，删除 shortcut 和 toggleActions
                updated_button.pop('shortcut', None)
                updated_button.pop('toggleActions', None)
                # 确保有 multiActions 字段
                if 'multiActions' not in updated_button:
                    updated_button['multiActions'] = []
            elif new_type == 'toggle':
                # 激活模式：只保留 toggleActions，删除 shortcut 和 multiActions
                updated_button.pop('shortcut', None)
                updated_button.pop('multiActions', None)
                # 确保有 toggleActions 字段
                if 'toggleActions' not in updated_button:
                    updated_button['toggleActions'] = {}
            
            buttons[i] = updated_button
            save_buttons(buttons)
            
            return updated_button
    
    return None

def delete_button(button_id: str) -> bool:
    """删除按钮"""
    buttons = load_buttons()
    original_count = len(buttons)
    
    buttons = [b for b in buttons if b.get("id") != button_id]
    
    if len(buttons) < original_count:
        save_buttons(buttons)
        return True
    
    return False
