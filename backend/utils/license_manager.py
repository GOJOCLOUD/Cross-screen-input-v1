#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
授权状态管理模块
管理软件的激活状态和功能权限
"""

import os
import json
import hashlib
import base64
import time
from typing import Optional, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import threading

from .activation import validate_builtin_activation_code
from .machine_id import get_machine_code


class LicenseManager:
    """许可证管理器"""
    
    def __init__(self):
        self.backend = default_backend()
        self._lock = threading.Lock()
        self._is_activated = None
        self._activation_code = None
        self._license_file = self._get_license_file_path()
        self._encryption_key = self._get_encryption_key()
        
    def _get_license_file_path(self) -> str:
        """
        获取许可证文件路径
        
        返回:
            许可证文件的完整路径
        """
        # 使用系统临时目录存储许可证
        if os.name == 'nt':  # Windows
            license_dir = os.path.join(os.environ.get('APPDATA', ''), 'KPSR')
        else:  # macOS/Linux
            license_dir = os.path.join(os.path.expanduser('~'), '.kpsr')
        
        if not os.path.exists(license_dir):
            os.makedirs(license_dir, exist_ok=True)
        
        # 使用隐藏文件名
        return os.path.join(license_dir, '.license')
    
    def _get_encryption_key(self) -> bytes:
        """
        获取加密密钥（基于系统信息派生）
        
        返回:
            32字节的加密密钥
        """
        # 使用机器码作为密钥派生基础
        machine_code = get_machine_code()
        
        # 使用固定的盐值确保同一机器的密钥一致
        salt = b'KPSR_LICENSE_KEY_SALT_2024'
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=self.backend
        )
        
        return kdf.derive(machine_code.encode())
    
    def _encrypt_data(self, data: str) -> str:
        """
        加密数据
        
        参数:
            data: 要加密的字符串
            
        返回:
            Base64编码的加密数据
        """
        fernet = Fernet(base64.urlsafe_b64encode(self._encryption_key))
        encrypted = fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """
        解密数据
        
        参数:
            encrypted_data: Base64编码的加密数据
            
        返回:
            解密后的字符串
        """
        try:
            fernet = Fernet(base64.urlsafe_b64encode(self._encryption_key))
            decrypted = fernet.decrypt(base64.urlsafe_b64decode(encrypted_data))
            return decrypted.decode()
        except Exception:
            raise ValueError("Invalid encrypted data")
    
    def _load_license(self) -> Optional[dict]:
        """
        从文件加载许可证
        
        返回:
            许可证数据字典，如果加载失败则返回None
        """
        try:
            if not os.path.exists(self._license_file):
                return None
            
            with open(self._license_file, 'r', encoding='utf-8') as f:
                encrypted_data = f.read().strip()
            
            decrypted_data = self._decrypt_data(encrypted_data)
            return json.loads(decrypted_data)
        except Exception:
            return None
    
    def _save_license(self, license_data: dict) -> bool:
        """
        保存许可证到文件
        
        参数:
            license_data: 许可证数据字典
            
        返回:
            是否保存成功
        """
        try:
            data_str = json.dumps(license_data, separators=(',', ':'))
            encrypted_data = self._encrypt_data(data_str)
            
            with open(self._license_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
            
            return True
        except Exception:
            return False
    
    def activate(self, activation_code: str) -> Tuple[bool, str]:
        """
        激活软件
        
        参数:
            activation_code: 激活码
            
        返回:
            (success, message) 激活结果和消息
        """
        with self._lock:
            try:
                # 获取当前机器码
                machine_code = get_machine_code()
                
                # 验证激活码
                is_valid, error_msg = validate_builtin_activation_code(machine_code, activation_code)
                if not is_valid:
                    return False, error_msg or "Invalid activation code"
                
                # 保存激活信息
                license_data = {
                    'activation_code': activation_code,
                    'machine_code': machine_code,
                    'activated_at': int(time.time()),
                    'version': '1.0'
                }
                
                if self._save_license(license_data):
                    self._is_activated = True
                    self._activation_code = activation_code
                    return True, "Activation successful"
                else:
                    return False, "Failed to save license"
                    
            except Exception as e:
                return False, f"Activation failed: {str(e)}"
    
    def deactivate(self) -> bool:
        """
        停用软件
        
        返回:
            是否停用成功
        """
        with self._lock:
            try:
                if os.path.exists(self._license_file):
                    os.remove(self._license_file)
                self._is_activated = False
                self._activation_code = None
                return True
            except Exception:
                return False
    
    def is_activated(self) -> bool:
        """
        检查软件是否已激活
        
        返回:
            是否已激活
        """
        with self._lock:
            if self._is_activated is not None:
                return self._is_activated
            
            # 加载许可证文件
            license_data = self._load_license()
            if license_data is None:
                self._is_activated = False
                return False
            
            # 验证许可证
            try:
                machine_code = get_machine_code()
                activation_code = license_data.get('activation_code')
                
                if not activation_code:
                    self._is_activated = False
                    return False
                
                # 验证激活码
                is_valid, _ = validate_builtin_activation_code(machine_code, activation_code)
                self._is_activated = is_valid
                self._activation_code = activation_code if is_valid else None
                
                return is_valid
            except Exception:
                self._is_activated = False
                return False
    
    def get_activation_info(self) -> Optional[dict]:
        """
        获取激活信息
        
        返回:
            激活信息字典，如果未激活则返回None
        """
        with self._lock:
            if not self.is_activated():
                return None
            
            license_data = self._load_license()
            if license_data:
                # 移除敏感信息
                return {
                    'machine_code': license_data.get('machine_code'),
                    'activated_at': license_data.get('activated_at'),
                    'version': license_data.get('version')
                }
            return None
    
    def check_feature_access(self, feature_name: str) -> bool:
        """
        检查功能访问权限
        
        参数:
            feature_name: 功能名称
            
        返回:
            是否允许访问该功能
        """
        # 如果软件已激活，允许所有功能
        if self.is_activated():
            return True
        
        # 如果未激活，不允许任何功能
        return False


# 全局许可证管理器实例
_license_manager = None
_manager_lock = threading.Lock()


def get_license_manager() -> LicenseManager:
    """
    获取全局许可证管理器实例（单例模式）
    
    返回:
        LicenseManager实例
    """
    global _license_manager
    
    with _manager_lock:
        if _license_manager is None:
            _license_manager = LicenseManager()
    
    return _license_manager


def check_activation() -> bool:
    """
    检查软件激活状态（便捷函数）
    
    返回:
        是否已激活
    """
    manager = get_license_manager()
    return manager.is_activated()


def activate_license(activation_code: str) -> Tuple[bool, str]:
    """
    激活许可证（便捷函数）
    
    参数:
        activation_code: 激活码
        
    返回:
        (success, message) 激活结果和消息
    """
    manager = get_license_manager()
    return manager.activate(activation_code)


def deactivate_license() -> bool:
    """
    停用许可证（便捷函数）
    
    返回:
        是否停用成功
    """
    manager = get_license_manager()
    return manager.deactivate()


def get_activation_info() -> Optional[dict]:
    """
    获取激活信息（便捷函数）
    
    返回:
        激活信息字典，如果未激活则返回None
    """
    manager = get_license_manager()
    return manager.get_activation_info()


def check_feature_access(feature_name: str) -> bool:
    """
    检查功能访问权限（便捷函数）
    
    参数:
        feature_name: 功能名称
        
    返回:
        是否允许访问该功能
    """
    manager = get_license_manager()
    return manager.check_feature_access(feature_name)


__all__ = [
    'LicenseManager',
    'get_license_manager',
    'check_activation',
    'activate_license',
    'deactivate_license',
    'get_activation_info',
    'check_feature_access',
]