#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络配置管理
控制网络访问范围和安全设置
"""

import os
import json
import secrets
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from pydantic import BaseModel

# 导入SSL证书工具
try:
    from utils.ssl_cert import check_certificates, generate_self_signed_cert
except ImportError:
    print("[WARNING] SSL证书工具导入失败，HTTPS功能将不可用")
    check_certificates = None
    generate_self_signed_cert = None

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "network_config.json")

class NetworkConfig(BaseModel):
    """网络配置模型"""
    # 访问控制模式
    access_mode: str = "private"  # "private" (私有网络), "lan" (局域网), "all" (所有网络)
    
    # 身份验证设置
    auth_enabled: bool = False  # 是否启用身份验证
    auth_token: Optional[str] = None  # 验证令牌
    token_expiry: Optional[datetime] = None  # 令牌过期时间
    
    # 设备管理
    paired_devices: Dict[str, Dict] = {}  # 已配对设备 {device_id: {name, paired_at, last_seen}}
    
    # 安全设置
    max_text_length: int = 10 * 1024 * 1024  # 最大文本长度 (10MB)
    request_timeout: int = 30  # 请求超时时间 (秒)
    max_retries: int = 3  # 最大重试次数
    
    # HTTPS 设置
    https_enabled: bool = False  # 是否启用 HTTPS
    cert_file: Optional[str] = None  # 证书文件路径
    key_file: Optional[str] = None  # 私钥文件路径
    
    # CORS 设置
    allowed_origins: List[str] = []  # 允许的来源列表

class NetworkManager:
    """网络管理器"""
    
    def __init__(self):
        self.config = self.load_config()
        # 初始化允许的来源列表
        if not self.config.allowed_origins:
            self.update_allowed_origins()
            self.save_config()
    
    def load_config(self) -> NetworkConfig:
        """加载配置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 处理日期时间字段
                if 'token_expiry' in data and data['token_expiry']:
                    data['token_expiry'] = datetime.fromisoformat(data['token_expiry'])
                
                return NetworkConfig(**data)
        except Exception as e:
            print(f"[WARNING] 加载网络配置失败: {e}，使用默认配置")
        
        return NetworkConfig()
    
    def save_config(self) -> bool:
        """保存配置"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            
            # 转换为字典
            data = self.config.dict()
            
            # 处理日期时间字段
            if data['token_expiry']:
                data['token_expiry'] = data['token_expiry'].isoformat()
            
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"[ERROR] 保存网络配置失败: {e}")
            return False
    
    def is_access_allowed(self, ip: str) -> bool:
        """检查IP是否允许访问"""
        if self.config.access_mode == "all":
            return True
        
        return self.is_private_ip(ip)
    
    def is_private_ip(self, ip: str) -> bool:
        """检查是否为私有IP"""
        # localhost
        if ip in ['127.0.0.1', 'localhost']:
            return True
        
        # 解析IP
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            
            # 检查 10.0.0.0/8（手机热点网络）
            if parts[0] == '10':
                return True
            
            # 检查 172.16.0.0/12（私有网络）
            if parts[0] == '172' and 16 <= int(parts[1]) <= 31:
                return True
            
            # 检查 192.168.0.0/16（私有网络）
            if parts[0] == '192' and parts[1] == '168':
                return True
            
            return False
        except:
            return False
    
    def generate_auth_token(self, expiry_hours: int = 24) -> str:
        """生成验证令牌"""
        self.config.auth_token = secrets.token_urlsafe(32)
        self.config.token_expiry = datetime.now() + timedelta(hours=expiry_hours)
        self.config.auth_enabled = True
        self.save_config()
        return self.config.auth_token
    
    def verify_auth_token(self, token: str) -> bool:
        """验证令牌"""
        if not self.config.auth_enabled or not self.config.auth_token:
            return False
        
        # 检查令牌是否匹配
        if secrets.compare_digest(token, self.config.auth_token):
            # 检查令牌是否过期
            if self.config.token_expiry and datetime.now() > self.config.token_expiry:
                self.config.auth_enabled = False
                self.save_config()
                return False
            return True
        
        return False
    
    def add_paired_device(self, device_id: str, name: str) -> bool:
        """添加配对设备"""
        try:
            self.config.paired_devices[device_id] = {
                "name": name,
                "paired_at": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat()
            }
            return self.save_config()
        except Exception as e:
            print(f"[ERROR] 添加配对设备失败: {e}")
            return False
    
    def remove_paired_device(self, device_id: str) -> bool:
        """移除配对设备"""
        try:
            if device_id in self.config.paired_devices:
                del self.config.paired_devices[device_id]
                return self.save_config()
            return False
        except Exception as e:
            print(f"[ERROR] 移除配对设备失败: {e}")
            return False
    
    def update_device_last_seen(self, device_id: str) -> bool:
        """更新设备最后访问时间"""
        try:
            if device_id in self.config.paired_devices:
                self.config.paired_devices[device_id]["last_seen"] = datetime.now().isoformat()
                return self.save_config()
            return False
        except Exception as e:
            print(f"[ERROR] 更新设备访问时间失败: {e}")
            return False
    
    def is_device_paired(self, device_id: str) -> bool:
        """检查设备是否已配对"""
        return device_id in self.config.paired_devices
    
    def get_access_mode_description(self) -> str:
        """获取访问模式描述"""
        descriptions = {
            "private": "仅私有网络访问 (10.x.x.x, 172.16.x.x-172.31.x.x, 192.168.x.x)",
            "lan": "局域网访问 (包含所有私有网络范围)",
            "all": "所有网络访问 (不限制IP地址)"
        }
        return descriptions.get(self.config.access_mode, "未知模式")
    
    def enable_https(self, force_generate: bool = False) -> bool:
        """启用HTTPS支持"""
        if not check_certificates or not generate_self_signed_cert:
            print("[ERROR] SSL证书工具不可用，无法启用HTTPS")
            return False
        
        # 检查证书状态
        cert_status = check_certificates()
        
        # 如果证书不存在或强制生成，则生成新证书
        if not cert_status.get("exists") or force_generate:
            print("[INFO] 正在生成SSL证书...")
            if not generate_self_signed_cert():
                print("[ERROR] 生成SSL证书失败")
                return False
            
            # 重新检查证书状态
            cert_status = check_certificates()
            if not cert_status.get("exists"):
                print("[ERROR] 证书生成后仍然无效")
                return False
        
        # 更新配置
        self.config.https_enabled = True
        self.config.cert_file = cert_status.get("cert_file")
        self.config.key_file = cert_status.get("key_file")
        
        return self.save_config()
    
    def disable_https(self) -> bool:
        """禁用HTTPS支持"""
        self.config.https_enabled = False
        self.config.cert_file = None
        self.config.key_file = None
        return self.save_config()
    
    def get_ssl_context(self):
        """获取SSL上下文"""
        if not self.config.https_enabled:
            return None
        
        if not self.config.cert_file or not self.config.key_file:
            return None
        
        if not os.path.exists(self.config.cert_file) or not os.path.exists(self.config.key_file):
            print("[WARNING] SSL证书文件不存在，HTTPS不可用")
            return None
        
        try:
            # 创建SSL上下文
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(
                certfile=self.config.cert_file,
                keyfile=self.config.key_file
            )
            return ssl_context
        except Exception as e:
            print(f"[ERROR] 创建SSL上下文失败: {e}")
            return None

    def set_access_mode(self, mode: str) -> bool:
        """设置访问模式"""
        if mode in ["private", "lan", "all"]:
            self.config.access_mode = mode
            # 根据访问模式更新允许的来源
            self.update_allowed_origins()
            return self.save_config()
        return False
    
    def update_allowed_origins(self):
        """根据访问模式更新允许的来源列表"""
        # 清空现有列表
        self.config.allowed_origins = []
        
        if self.config.access_mode == "all":
            # 所有模式：允许所有来源，但需要通过其他安全机制保护
            self.config.allowed_origins = ["*"]
        elif self.config.access_mode == "lan":
            # 局域网模式：允许私有网络IP和localhost
            self.config.allowed_origins = [
                "http://localhost:*",
                "https://localhost:*",
                "http://127.0.0.1:*",
                "https://127.0.0.1:*",
                "http://0.0.0.0:*",
                "https://0.0.0.0:*"
            ]
            # 添加私有网络IP模式
            self.config.allowed_origins.extend([
                "http://10.*",
                "https://10.*",
                "http://172.16.*",
                "https://172.16.*",
                "http://172.17.*",
                "https://172.17.*",
                "http://172.18.*",
                "https://172.18.*",
                "http://172.19.*",
                "https://172.19.*",
                "http://172.20.*",
                "https://172.20.*",
                "http://172.21.*",
                "https://172.21.*",
                "http://172.22.*",
                "https://172.22.*",
                "http://172.23.*",
                "https://172.23.*",
                "http://172.24.*",
                "https://172.24.*",
                "http://172.25.*",
                "https://172.25.*",
                "http://172.26.*",
                "https://172.26.*",
                "http://172.27.*",
                "https://172.27.*",
                "http://172.28.*",
                "https://172.28.*",
                "http://172.29.*",
                "https://172.29.*",
                "http://172.30.*",
                "https://172.30.*",
                "http://172.31.*",
                "https://172.31.*",
                "http://192.168.*",
                "https://192.168.*"
            ])
        elif self.config.access_mode == "private":
            # 私有模式：只允许localhost和本机IP
            self.config.allowed_origins = [
                "http://localhost:*",
                "https://localhost:*",
                "http://127.0.0.1:*",
                "https://127.0.0.1:*",
                "http://0.0.0.0:*",
                "https://0.0.0.0:*"
            ]
    
    def is_origin_allowed(self, origin: str) -> bool:
        """检查来源是否被允许"""
        if not origin:
            return True  # 非跨域请求
        
        # 如果允许所有来源
        if "*" in self.config.allowed_origins:
            return True
        
        # 检查是否匹配任何允许的模式
        for allowed_pattern in self.config.allowed_origins:
            if self.match_origin_pattern(origin, allowed_pattern):
                return True
        
        return False
    
    def match_origin_pattern(self, origin: str, pattern: str) -> bool:
        """检查来源是否匹配模式"""
        # 处理通配符模式
        if "*" in pattern:
            # 将模式转换为正则表达式
            regex_pattern = pattern.replace("*", ".*").replace(".", "\\.")
            regex_pattern = f"^{regex_pattern}$"
            
            import re
            return re.match(regex_pattern, origin) is not None
        
        # 精确匹配
        return origin == pattern
    
    def add_allowed_origin(self, origin: str) -> bool:
        """添加允许的来源"""
        if origin not in self.config.allowed_origins:
            self.config.allowed_origins.append(origin)
            return self.save_config()
        return True
    
    def remove_allowed_origin(self, origin: str) -> bool:
        """移除允许的来源"""
        if origin in self.config.allowed_origins:
            self.config.allowed_origins.remove(origin)
            return self.save_config()
        return False

# 全局网络管理器实例
network_manager = NetworkManager()