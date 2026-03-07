#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成密钥对并更新内置公钥

在Mac上完成操作
"""

import sys
import os
import json

# 添加backend目录到Python路径
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, backend_dir)

from utils.activation import ActivationKeyGenerator


def main():
    print("=" * 60)
    print("生成密钥对并更新内置公钥")
    print("=" * 60)
    
    # 生成密钥对
    generator = ActivationKeyGenerator()
    private_key, public_key = generator.generate_key_pair()
    private_pem, public_pem = generator.serialize_keys(private_key, public_key)
    
    # 保存密钥对到文件
    keys_data = {
        'private_key': private_pem,
        'public_key': public_pem,
        'generated_at': int(time.time()),
        'version': '1.0'
    }
    
    with open('activation_keys.json', 'w', encoding='utf-8') as f:
        json.dump(keys_data, f, indent=2)
    
    print("\n密钥对已生成并保存到 activation_keys.json")
    print("\n公钥内容（请复制到 activation.py 中的 BUILTIN_PUBLIC_KEY）：")
    print("=" * 60)
    print(public_pem)
    print("=" * 60)
    
    print("\n请将上述公钥复制到 backend/utils/activation.py 文件中的 BUILTIN_PUBLIC_KEY 变量")


if __name__ == "__main__":
    import time
    main()