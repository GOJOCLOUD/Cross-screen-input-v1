#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理模块
提供统一的日志记录、保存和读取功能
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import threading

# 导入统一配置
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LOGS_DIR as CONFIG_LOGS_DIR

# 日志目录（使用统一配置）
LOGS_DIR = Path(CONFIG_LOGS_DIR)

# 确保日志目录存在
LOGS_DIR.mkdir(exist_ok=True)

# 日志锁，防止并发写入问题
log_lock = threading.Lock()

class AppLogger:
    """应用日志管理器"""
    
    def __init__(self, name: str = "app") -> None:
        self.name = name
        self.log_file = LOGS_DIR / f"{name}.log"
        self.json_log_file = LOGS_DIR / f"{name}.json"
        
        # 配置Python logging
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 清除已有的handler
        self.logger.handlers.clear()
        
        # 文件handler
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-7s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # 控制台handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-7s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # 初始化JSON日志文件
        self._init_json_log()
    
    def _init_json_log(self) -> None:
        """初始化JSON日志文件"""
        if not self.json_log_file.exists():
            with open(self.json_log_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
    
    def _append_json_log(self, entry: Dict[str, Any]) -> None:
        """追加JSON日志条目"""
        with log_lock:
            try:
                # 读取现有日志
                with open(self.json_log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                
                # 追加新条目
                logs.append(entry)
                
                # 只保留最近10000条日志
                if len(logs) > 10000:
                    logs = logs[-10000:]
                
                # 写回文件
                with open(self.json_log_file, 'w', encoding='utf-8') as f:
                    json.dump(logs, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"写入JSON日志失败: {e}")
    
    def _create_entry(
        self, 
        level: str, 
        message: str, 
        source: str = "backend", 
        extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建日志条目"""
        return {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "source": source,
            "message": message,
            "extra": extra or {}
        }
    
    def debug(self, message: str, source: str = "backend", extra: Optional[Dict[str, Any]] = None) -> None:
        """调试日志"""
        self.logger.debug(f"[{source}] {message}")
        self._append_json_log(self._create_entry("DEBUG", message, source, extra))
    
    def info(self, message: str, source: str = "backend", extra: Optional[Dict[str, Any]] = None) -> None:
        """信息日志"""
        self.logger.info(f"[{source}] {message}")
        self._append_json_log(self._create_entry("INFO", message, source, extra))
    
    def warning(self, message: str, source: str = "backend", extra: Optional[Dict[str, Any]] = None) -> None:
        """警告日志"""
        self.logger.warning(f"[{source}] {message}")
        self._append_json_log(self._create_entry("WARNING", message, source, extra))
    
    def error(self, message: str, source: str = "backend", extra: Optional[Dict[str, Any]] = None) -> None:
        """错误日志"""
        self.logger.error(f"[{source}] {message}")
        self._append_json_log(self._create_entry("ERROR", message, source, extra))
    
    def log_frontend(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录前端日志"""
        level = level.upper()
        source = "frontend"
        
        if level == "DEBUG":
            self.logger.debug(f"[{source}] {message}")
        elif level == "INFO":
            self.logger.info(f"[{source}] {message}")
        elif level == "WARNING" or level == "WARN":
            self.logger.warning(f"[{source}] {message}")
        elif level == "ERROR":
            self.logger.error(f"[{source}] {message}")
        else:
            self.logger.info(f"[{source}] {message}")
        
        self._append_json_log(self._create_entry(level, message, source, extra))
    
    def get_logs(self, 
                 limit: int = 100, 
                 level: Optional[str] = None, 
                 source: Optional[str] = None,
                 start_time: Optional[str] = None,
                 end_time: Optional[str] = None) -> List[dict]:
        """获取日志"""
        try:
            with open(self.json_log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            # 过滤
            if level:
                logs = [log for log in logs if log.get("level", "").upper() == level.upper()]
            
            if source:
                logs = [log for log in logs if log.get("source", "").lower() == source.lower()]
            
            if start_time:
                logs = [log for log in logs if log.get("timestamp", "") >= start_time]
            
            if end_time:
                logs = [log for log in logs if log.get("timestamp", "") <= end_time]
            
            # 返回最新的limit条
            return logs[-limit:]
        except Exception as e:
            print(f"读取日志失败: {e}")
            return []
    
    def clear_logs(self) -> bool:
        """清空日志"""
        with log_lock:
            try:
                # 清空文本日志
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    f.write("")
                
                # 清空JSON日志
                with open(self.json_log_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                
                return True
            except Exception as e:
                print(f"清空日志失败: {e}")
                return False
    
    def get_log_stats(self) -> Dict[str, Any]:
        """获取日志统计"""
        try:
            with open(self.json_log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            stats = {
                "total": len(logs),
                "by_level": {},
                "by_source": {},
                "log_file": str(self.log_file),
                "json_log_file": str(self.json_log_file)
            }
            
            for log in logs:
                level = log.get("level", "UNKNOWN")
                source = log.get("source", "unknown")
                
                stats["by_level"][level] = stats["by_level"].get(level, 0) + 1
                stats["by_source"][source] = stats["by_source"].get(source, 0) + 1
            
            return stats
        except Exception as e:
            return {"error": str(e)}


# 创建全局日志实例
app_logger = AppLogger("app")

# 便捷函数
def debug(message: str, source: str = "backend", extra: Optional[Dict[str, Any]] = None) -> None:
    """记录调试日志"""
    app_logger.debug(message, source, extra)


def info(message: str, source: str = "backend", extra: Optional[Dict[str, Any]] = None) -> None:
    """记录信息日志"""
    app_logger.info(message, source, extra)


def warning(message: str, source: str = "backend", extra: Optional[Dict[str, Any]] = None) -> None:
    """记录警告日志"""
    app_logger.warning(message, source, extra)


def error(message: str, source: str = "backend", extra: Optional[Dict[str, Any]] = None) -> None:
    """记录错误日志"""
    app_logger.error(message, source, extra)


def log_frontend(level: str, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
    """记录前端日志"""
    app_logger.log_frontend(level, message, extra)


def get_logs(**kwargs) -> List[Dict[str, Any]]:
    """获取日志"""
    return app_logger.get_logs(**kwargs)


def clear_logs() -> bool:
    """清空日志"""
    return app_logger.clear_logs()


def get_log_stats() -> Dict[str, Any]:
    """获取日志统计"""
    return app_logger.get_log_stats()
