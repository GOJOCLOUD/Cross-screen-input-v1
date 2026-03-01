#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的测试服务器
用于测试端口7593是否正常工作
"""

import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "KPSR跨屏输入服务器正在运行", "port": 7593}

if __name__ == "__main__":
    print("启动测试服务器，端口: 7593")
    uvicorn.run(app, host="0.0.0.0", port=7593)