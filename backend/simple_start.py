#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的启动脚本
绕过有问题的模块，直接启动服务器
"""

import sys
import os
import uvicorn

def main():
    # 设置端口
    port = 7593
    host = "0.0.0.0"
    
    print(f"正在启动服务器，端口: {port}")
    
    # 直接启动uvicorn，不导入有问题的模块
    try:
        uvicorn.run(
            "fastapi.app:app",
            host=host,
            port=port,
            log_level="info"
        )
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()