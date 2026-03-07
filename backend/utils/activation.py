#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
激活码生成和验证模块
使用多重加密算法保护激活码系统

在Mac上完成操作
"""

import hashlib
import base64
import time
import json
from typing import Optional, Tuple, Dict
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import os


class ActivationKeyGenerator:
    """激活码生成器（服务器端使用）"""
    
    def __init__(self):
        self.backend = default_backend()
    
    def generate_key_pair(self) -> Tuple[bytes, bytes]:
        """
        生成RSA密钥对
        
        返回:
            (private_key, public_key) 私钥和公钥
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=self.backend
        )
        public_key = private_key.public_key()
        
        return private_key, public_key
    
    def serialize_keys(self, private_key, public_key) -> Tuple[str, str]:
        """
        序列化密钥对
        
        返回:
            (private_key_pem, public_key_pem) PEM格式的密钥字符串
        """
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        return private_pem, public_pem
    
    def generate_activation_code(self, machine_code: str, private_key: bytes, 
                            expiry_days: int = 365) -> str:
        """
        生成激活码
        
        参数:
            machine_code: 机器码
            private_key: RSA私钥
            expiry_days: 有效天数
            
        返回:
            激活码字符串
        """
        # 1. 创建激活数据
        timestamp = int(time.time())
        expiry_timestamp = timestamp + (expiry_days * 24 * 3600)
        
        activation_data = {
            'mc': machine_code,
            'ts': timestamp,
            'exp': expiry_timestamp,
            'salt': os.urandom(16).hex()
        }
        
        # 2. 将数据转换为JSON字符串
        data_str = json.dumps(activation_data, separators=(',', ':'))
        
        # 3. 使用多重哈希
        hash1 = hashlib.sha256(data_str.encode()).hexdigest()
        hash2 = hashlib.sha384(hash1.encode()).hexdigest()
        final_hash = hash1[:32] + hash2[:32]
        
        # 4. 将哈希添加到数据中
        activation_data['hash'] = final_hash
        data_str = json.dumps(activation_data, separators=(',', ':'))
        
        # 5. 使用AES加密数据
        aes_key = self._derive_aes_key(machine_code, activation_data['salt'])
        encrypted_data = self._aes_encrypt(data_str.encode(), aes_key)
        
        # 6. 使用RSA加密AES密钥
        rsa_private_key = serialization.load_pem_private_key(
            private_key,
            password=None,
            backend=self.backend
        )
        
        encrypted_key = rsa_private_key.public_key().encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # 7. 组合加密数据
        combined = encrypted_key + b'|' + encrypted_data
        
        # 8. Base64编码
        activation_code = base64.b64encode(combined).decode('utf-8')
        
        # 9. 格式化为XXXX-XXXX-XXXX...格式
        formatted_code = '-'.join([activation_code[i:i+4] for i in range(0, len(activation_code), 4)])
        
        return formatted_code
    
    def _derive_aes_key(self, machine_code: str, salt: str) -> bytes:
        """
        从机器码派生AES密钥
        
        参数:
            machine_code: 机器码
            salt: 盐值
            
        返回:
            32字节的AES密钥
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=bytes.fromhex(salt),
            iterations=100000,
            backend=self.backend
        )
        return kdf.derive(machine_code.encode())
    
    def _aes_encrypt(self, data: bytes, key: bytes) -> bytes:
        """
        AES加密
        
        参数:
            data: 要加密的数据
            key: AES密钥
            
        返回:
            加密后的数据
        """
        iv = os.urandom(16)
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=self.backend
        )
        encryptor = cipher.encryptor()
        
        # PKCS7填充
        pad_length = 16 - (len(data) % 16)
        padded_data = data + bytes([pad_length] * pad_length)
        
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        return iv + encrypted


class ActivationKeyValidator:
    """激活码验证器（客户端内置）"""
    
    def __init__(self, public_key_pem: str):
        """
        初始化验证器
        
        参数:
            public_key_pem: PEM格式的公钥
        """
        self.backend = default_backend()
        self.public_key = serialization.load_pem_public_key(
            public_key_pem.encode(),
            backend=self.backend
        )
    
    def validate_activation_code(self, machine_code: str, activation_code: str) -> Tuple[bool, Optional[str]]:
        """
        验证激活码
        
        参数:
            machine_code: 机器码
            activation_code: 激活码
            
        返回:
            (is_valid, error_message) 验证结果和错误信息
        """
        try:
            # 1. 移除格式化字符
            clean_code = activation_code.replace('-', '')
            
            # 2. Base64解码
            combined = base64.b64decode(clean_code.encode())
            
            # 3. 分离加密的密钥和数据
            parts = combined.split(b'|')
            if len(parts) != 2:
                return False, "Invalid activation code format"
            
            encrypted_key, encrypted_data = parts
            
            # 4. 使用RSA解密AES密钥
            aes_key = self.public_key.decrypt(
                encrypted_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # 5. 使用AES解密数据
            decrypted_data = self._aes_decrypt(encrypted_data, aes_key)
            
            # 6. 解析JSON数据
            activation_data = json.loads(decrypted_data.decode())
            
            # 7. 验证机器码
            if activation_data['mc'] != machine_code:
                return False, "Machine code mismatch"
            
            # 8. 验证哈希
            hash1 = hashlib.sha256(decrypted_data.decode().encode()).hexdigest()
            hash2 = hashlib.sha384(hash1.encode()).hexdigest()
            expected_hash = hash1[:32] + hash2[:32]
            
            if activation_data['hash'] != expected_hash:
                return False, "Invalid activation code signature"
            
            # 9. 验证有效期
            current_time = int(time.time())
            if current_time > activation_data['exp']:
                return False, "Activation code has expired"
            
            return True, None
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def _aes_decrypt(self, encrypted_data: bytes, key: bytes) -> bytes:
        """
        AES解密
        
        参数:
            encrypted_data: 加密的数据
            key: AES密钥
            
        返回:
            解密后的数据
        """
        iv = encrypted_data[:16]
        cipher_text = encrypted_data[16:]
        
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=self.backend
        )
        decryptor = cipher.decryptor()
        
        decrypted = decryptor.update(cipher_text) + decryptor.finalize()
        
        # 移除PKCS7填充
        pad_length = decrypted[-1]
        return decrypted[:-pad_length]


# 内置公钥（嵌入到程序中，不存储在外部文件中）
BUILTIN_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA4E8DSmAsRy0g2WBafRHL
EGWoMUVSMee2nwJP4uqNUs1RtFRFApDm/zosJvvDBSn599J8XPameJOqS9b4yid9
5mUsrEVb6mtrCeKkDGKXATpGnHDKl+plVVHVkLZCjXXzzehB7IqVgFUcyhlHsIWR
ytgP59D9ivYp7bAhFGOLe3+bxgm/V32DMKoJzh1A6vyf9VxTujpaCT449ilxueAq
0paNLXOMSX70GSgFdL3CpEpryCiITgSKHBPa13SIxKbSW0ymzzBVfznz/hUchfBZ
ioLWVOZFoNGEHRo6Nd/rs4jdWQLO0lX3ncUF+a6+EKKjKCK497bSoOq0jGY6bnty
hQIDAQAB
-----END PUBLIC KEY-----"""


def get_builtin_validator() -> ActivationKeyValidator:
    """
    获取内置的验证器实例
    
    返回:
        ActivationKeyValidator实例
    """
    return ActivationKeyValidator(BUILTIN_PUBLIC_KEY)


def validate_builtin_activation_code(machine_code: str, activation_code: str) -> Tuple[bool, Optional[str]]:
    """
    使用内置公钥验证激活码
    
    参数:
        machine_code: 机器码
        activation_code: 激活码
        
    返回:
        (is_valid, error_message) 验证结果和错误信息
    """
    validator = get_builtin_validator()
    return validator.validate_activation_code(machine_code, activation_code)


__all__ = [
    'ActivationKeyGenerator',
    'ActivationKeyValidator',
    'BUILTIN_PUBLIC_KEY',
    'get_builtin_validator',
    'validate_builtin_activation_code',
]