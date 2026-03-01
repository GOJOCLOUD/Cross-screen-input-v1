#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSL证书生成工具
用于生成自签名证书以支持HTTPS
"""

import os
import sys
import subprocess
import ssl
from datetime import datetime, timedelta
from pathlib import Path

# 证书目录
CERT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ssl")

def generate_self_signed_cert():
    """生成自签名证书"""
    try:
        # 确保证书目录存在
        os.makedirs(CERT_DIR, exist_ok=True)
        
        cert_file = os.path.join(CERT_DIR, "cert.pem")
        key_file = os.path.join(CERT_DIR, "key.pem")
        
        # 检查证书是否已存在且未过期
        if os.path.exists(cert_file) and os.path.exists(key_file):
            try:
                # 检查证书有效期
                with open(cert_file, 'r') as f:
                    cert_data = f.read()
                
                # 加载证书
                cert = ssl.PEM_cert_to_DER_cert(cert_data)
                cert_info = ssl.DER_cert_to_PEM_cert(cert)
                
                # 简单检查：如果证书文件存在且不为空，认为有效
                # 在生产环境中应该检查证书有效期
                if os.path.getsize(cert_file) > 0 and os.path.getsize(key_file) > 0:
                    print(f"[INFO] 证书已存在: {cert_file}")
                    return True
            except Exception as e:
                print(f"[WARNING] 检查现有证书失败: {e}，将重新生成")
        
        # 生成证书
        print("[INFO] 正在生成自签名证书...")
        
        # 证书配置
        cert_config = {
            "country": "CN",
            "state": "Beijing",
            "locality": "Beijing",
            "organization": "KPSR",
            "organizational_unit": "Cross-Screen Input",
            "common_name": "KPSR Cross-Screen Input",
            "email": "kpsr@localhost",
            "valid_days": 365
        }
        
        # 使用openssl生成证书
        subject = f"/C={cert_config['country']}/ST={cert_config['state']}/L={cert_config['locality']}/O={cert_config['organization']}/OU={cert_config['organizational_unit']}/CN={cert_config['common_name']}/emailAddress={cert_config['email']}"
        
        # 生成私钥
        key_cmd = [
            "openssl", "genrsa", "-out", key_file, "2048"
        ]
        
        # 生成证书
        cert_cmd = [
            "openssl", "req", "-new", "-x509", "-key", key_file, 
            "-out", cert_file, "-days", str(cert_config["valid_days"]),
            "-subj", subject
        ]
        
        # 执行命令
        try:
            print(f"[INFO] 生成私钥: {key_file}")
            result = subprocess.run(key_cmd, capture_output=True, text=True, check=True)
            
            print(f"[INFO] 生成证书: {cert_file}")
            result = subprocess.run(cert_cmd, capture_output=True, text=True, check=True)
            
            # 检查文件是否生成成功
            if os.path.exists(cert_file) and os.path.exists(key_file):
                print(f"[SUCCESS] 证书生成成功")
                print(f"  证书文件: {cert_file}")
                print(f"  私钥文件: {key_file}")
                print(f"  有效期: {cert_config['valid_days']} 天")
                return True
            else:
                print("[ERROR] 证书生成失败: 文件未创建")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] openssl命令执行失败: {e}")
            print(f"[ERROR] stdout: {e.stdout}")
            print(f"[ERROR] stderr: {e.stderr}")
            return False
        except FileNotFoundError:
            print("[ERROR] openssl未找到，请确保已安装OpenSSL")
            return False
            
    except Exception as e:
        print(f"[ERROR] 生成证书失败: {e}")
        return False

def check_certificates():
    """检查证书状态"""
    cert_file = os.path.join(CERT_DIR, "cert.pem")
    key_file = os.path.join(CERT_DIR, "key.pem")
    
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        return {
            "exists": False,
            "message": "证书文件不存在"
        }
    
    try:
        # 检查文件大小
        if os.path.getsize(cert_file) == 0 or os.path.getsize(key_file) == 0:
            return {
                "exists": False,
                "message": "证书文件为空"
            }
        
        # 尝试加载证书
        with open(cert_file, 'r') as f:
            cert_data = f.read()
        
        # 简单验证证书格式
        if "-----BEGIN CERTIFICATE-----" not in cert_data or "-----END CERTIFICATE-----" not in cert_data:
            return {
                "exists": False,
                "message": "证书格式无效"
            }
        
        with open(key_file, 'r') as f:
            key_data = f.read()
        
        if "-----BEGIN PRIVATE KEY-----" not in key_data or "-----END PRIVATE KEY-----" not in key_data:
            return {
                "exists": False,
                "message": "私钥格式无效"
            }
        
        return {
            "exists": True,
            "message": "证书有效",
            "cert_file": cert_file,
            "key_file": key_file
        }
        
    except Exception as e:
        return {
            "exists": False,
            "message": f"检查证书失败: {e}"
        }

def main():
    """主函数"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "check":
            # 检查证书状态
            result = check_certificates()
            print(f"[INFO] 证书状态: {result['message']}")
            if result.get("exists"):
                print(f"[INFO] 证书文件: {result.get('cert_file')}")
                print(f"[INFO] 私钥文件: {result.get('key_file')}")
            sys.exit(0 if result.get("exists") else 1)
        
        elif command == "generate":
            # 生成证书
            success = generate_self_signed_cert()
            sys.exit(0 if success else 1)
        
        else:
            print(f"[ERROR] 未知命令: {command}")
            print("用法: python ssl_cert.py [check|generate]")
            sys.exit(1)
    
    else:
        # 默认行为：检查证书，如果不存在则生成
        result = check_certificates()
        if not result.get("exists"):
            print("[INFO] 证书不存在，正在生成...")
            success = generate_self_signed_cert()
            sys.exit(0 if success else 1)
        else:
            print("[INFO] 证书已存在且有效")
            sys.exit(0)

if __name__ == "__main__":
    main()