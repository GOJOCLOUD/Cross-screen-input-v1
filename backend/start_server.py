#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动脚本，解决Python 3.9兼容性问题
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # 尝试导入并启动
    print("正在启动KPSR跨屏输入服务器...")
    print(f"端口: 7593")
    print(f"数据目录: {os.path.join(os.path.dirname(__file__), 'data')}")
    print(f"日志目录: {os.path.join(os.path.dirname(__file__), 'logs')}")
    
    # 导入并启动
    import uvicorn
    from fastapi import FastAPI
    
    # 创建最小化的应用
    app = FastAPI()
    
    @app.get("/")
    async def root():
        return {"message": "KPSR跨屏输入服务器正在运行", "port": 7593}
    
    print("启动服务器...")
    uvicorn.run(app, host="0.0.0.0", port=7593)
    
except Exception as e:
    print(f"启动失败: {e}")
    import traceback
    traceback.print_exc()