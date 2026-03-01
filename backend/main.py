#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI主应用
统一管理所有后端功能，包括剪贴板操作和页面跳转
"""

# 标准库
import os
import socket
import subprocess
import re
import json

# 第三方库
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response, JSONResponse
from pydantic import BaseModel

# 固定端口
FIXED_PORT = 7593

# 创建FastAPI应用实例
app = FastAPI(
    title="跨屏输入API",
    description="统一管理剪贴板操作和页面跳转的后端API",
    version="1.0.0"
)

# 从 config.py 导入路径配置
from config import PROJECT_ROOT, FRONTEND_DIR

# 挂载前端静态文件
if os.path.exists(FRONTEND_DIR):
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")

# 导入路由模块
from routes import clipboard, shortcut, button_config, logs, monitor, mouse, mouse_config, mouse_listener, desktop_api, network_config, heartbeat

# 注册路由
app.include_router(clipboard.router, prefix="/api/clipboard", tags=["clipboard"])
app.include_router(shortcut.router, prefix="/api/shortcut", tags=["shortcut"])
app.include_router(button_config.router, prefix="/api/button-config", tags=["button-config"])
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])
app.include_router(monitor.router, prefix="/api/monitor", tags=["monitor"])
app.include_router(mouse.router, prefix="/api/mouse", tags=["mouse"])
app.include_router(mouse_config.router, prefix="/api/mouse-config", tags=["mouse-config"])
app.include_router(mouse_listener.router, prefix="/api/mouse-listener", tags=["mouse-listener"])
app.include_router(desktop_api.router, prefix="/api/desktop", tags=["desktop"])
app.include_router(network_config.router, prefix="/api/network", tags=["network-config"])
app.include_router(heartbeat.router, prefix="/api/heartbeat", tags=["heartbeat"])

# 应用启动时自动启动鼠标监听器
@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    print("\n[INFO] 正在启动鼠标按键监听器...")
    try:
        from routes.mouse_listener import start_listener
        result = start_listener()
        if result.get('success'):
            print("[SUCCESS] 鼠标按键监听器已启动")
        else:
            print(f"[WARNING] 鼠标监听器启动失败: {result.get('message', '未知错误')}")
    except Exception as e:
        print(f"[WARNING] 鼠标监听器启动失败: {e}")

# 应用关闭时停止监听器
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    try:
        from routes.mouse_listener import stop_listener
        stop_listener()
        print("[INFO] 鼠标监听器已停止")
    except Exception as e:
        print(f"[WARNING] 停止监听器失败: {e}")

# 根路径返回desktop.html（仅限本机访问）
@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    """返回电脑端主页面（仅限127.0.0.1访问）"""
    client_ip = request.client.host
    
    # 电脑端界面只能本机访问
    if client_ip != "127.0.0.1":
        return HTMLResponse(
            content="<h1>403 Forbidden</h1><p>电脑端控制台仅限本机访问，请使用 /phone 访问手机界面</p>",
            status_code=403
        )
    
    desktop_html_path = os.path.join(FRONTEND_DIR, "desktop.html")
    if os.path.exists(desktop_html_path):
        with open(desktop_html_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    return HTMLResponse(content="<h1>跨屏输入</h1><p>前端文件未找到</p>")


# phone路径返回phone.html
@app.get("/phone", response_class=HTMLResponse)
async def phone() -> HTMLResponse:
    """返回手机端主页面"""
    phone_html_path = os.path.join(FRONTEND_DIR, "phone.html")
    if os.path.exists(phone_html_path):
        with open(phone_html_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    return HTMLResponse(content="<h1>跨屏输入</h1><p>前端文件未找到</p>")


# pair路径返回pair.html
@app.get("/pair", response_class=HTMLResponse)
async def pair() -> HTMLResponse:
    """返回设备配对页面"""
    pair_html_path = os.path.join(FRONTEND_DIR, "pair.html")
    if os.path.exists(pair_html_path):
        with open(pair_html_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    return HTMLResponse(content="<h1>跨屏输入</h1><p>配对页面未找到</p>")


# send路径返回phone.html（GET请求）
@app.get("/send", response_class=HTMLResponse)
async def send() -> HTMLResponse:
    """返回手机端主页面（兼容旧路径）"""
    return await phone()

# 定义请求模型
class SendRequest(BaseModel):
    """发送请求的数据模型"""
    msg: str


# send路径处理POST请求，实现复制到剪贴板功能
@app.post("/send")
async def send_post(request: Request) -> dict:
    """处理POST请求，复制文本到剪贴板"""
    from routes.clipboard import copy_to_clipboard
    
    try:
        body = await request.json()
        copy_data = SendRequest(**body)
        
        # 调用剪贴板功能
        return await copy_to_clipboard(request, copy_data)
    except Exception as e:
        return {
            "status": "error",
            "message": f"处理请求失败: {str(e)}"
        }

# 获取本地IP地址
def get_local_ip() -> str:
    """获取本机局域网IP地址"""
    try:
        # 使用私有网络地址来获取本地IP，避免使用公共DNS
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.0.0.1", 80))  # 使用私有网络地址
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


# 动态CORS中间件
@app.middleware("http")
async def dynamic_cors_middleware(request: Request, call_next):
    """动态CORS中间件，根据请求来源和访问模式决定是否允许跨域"""
    origin = request.headers.get("origin")
    
    # 如果没有Origin头，不是跨域请求，直接放行
    if not origin:
        response = await call_next(request)
        return response
    
    # 检查是否允许此来源
    if network_manager.is_origin_allowed(origin):
        response = await call_next(request)
        
        # 添加CORS头
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        
        # 处理预检请求
        if request.method == "OPTIONS":
            return Response(status_code=200)
        
        return response
    
    # 不允许的来源，返回错误
    return JSONResponse(
        status_code=403,
        content={
            "detail": "CORS policy violation",
            "message": f"来源 {origin} 不在允许列表中",
            "access_mode": network_manager.config.access_mode
        }
    )

# 从 utils 导入网络配置管理器
from utils.network_config import network_manager

# 检查是否为私有IP
def is_private_ip(ip: str) -> bool:
    """检查IP是否在允许的网络范围内"""
    return network_manager.is_access_allowed(ip)

# 全局访问控制中间件
@app.middleware("http")
async def access_control_middleware(request: Request, call_next) -> Response:
    """访问控制中间件"""
    # 获取客户端IP
    client_ip = request.client.host
    
    # 检查IP是否允许访问
    if not is_private_ip(client_ip):
        return JSONResponse(
            status_code=403,
            content={
                "detail": "Forbidden: Access not allowed from this network",
                "message": f"当前访问模式: {network_manager.get_access_mode_description()}",
                "client_ip": client_ip,
                "access_mode": network_manager.config.access_mode
            }
        )
    
    # 检查身份验证（如果启用）
    if network_manager.config.auth_enabled:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Unauthorized: Authentication required",
                    "message": "需要提供验证令牌"
                }
            )
        
        token = auth_header.split(" ")[1]
        if not network_manager.verify_auth_token(token):
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Unauthorized: Invalid or expired token",
                    "message": "验证令牌无效或已过期"
                }
            )
    
    # 继续处理请求
    response = await call_next(request)
    return response

# 健康检查端点
@app.get("/health")
async def health_check() -> dict:
    """返回服务健康状态"""
    return {
        "status": "healthy",
        "message": "服务运行正常",
        "local_ip": get_local_ip()
    }

if __name__ == "__main__":
    import uvicorn
    import sys
    
    # 检测是否在打包环境中运行
    is_frozen = getattr(sys, 'frozen', False)
    
    # 使用固定端口 7593，启动前自动清理占用该端口的进程
    port = FIXED_PORT
    
    # 清理占用端口的进程
    try:
        from utils.port_manager import kill_process_on_port
        if not kill_process_on_port(port):
            print(f"[WARNING] 清理端口 {port} 失败，可能无法启动服务")
        else:
            import time
            time.sleep(0.5)  # 等待进程完全退出
    except Exception as e:
        print(f"[WARNING] 清理端口时出错: {e}")
    
    # 获取本地IP
    local_ip = get_local_ip()
    
    # 显示localhost和私有网络地址
    print("=" * 60)
    print("FastAPI服务器启动信息")
    print("=" * 60)
    print(f"服务端口: {port}")
    print("服务地址:")
    print(f"  - http://localhost:{port}")
    
    # 获取所有网络接口的私有IP地址
    try:
        # Windows使用ipconfig命令
        result = subprocess.run(['ipconfig'], capture_output=True, text=True)
        # 查找所有私有网络IP地址
        private_ips = re.findall(r'IPv4 Address[^\d]*(10\.\d+\.\d+\.\d+)', result.stdout)
        private_ips.extend(re.findall(r'IPv4 Address[^\d]*(172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)', result.stdout))
        private_ips.extend(re.findall(r'IPv4 Address[^\d]*(192\.168\.\d+\.\d+)', result.stdout))
        
        # 如果没有找到，尝试其他格式
        if not private_ips:
            private_ips = re.findall(r'(10\.\d+\.\d+\.\d+)', result.stdout)
            private_ips.extend(re.findall(r'(172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)', result.stdout))
            private_ips.extend(re.findall(r'(192\.168\.\d+\.\d+)', result.stdout))
        
        # 去重并显示找到的私有IP地址
        unique_private_ips = list(set(private_ips))
        for ip in unique_private_ips:
            print(f"  - http://{ip}:{port}")
    except Exception:
        pass
    
    print("")
    print("重要说明:")
    print("  - 本服务只允许电脑本机访问和私有网络访问")
    print("  - 请将您的手机连接到与电脑相同的私有网络")
    print("  - 然后在手机浏览器中使用私有网络地址访问")
    print(f"  - 私有网络地址格式: 10.x.x.x:{port}, 172.16.x.x-{port}, 192.168.x.x:{port}")
    print(f"  - 固定端口: {port}")
    print("")
    print("可用端点:")
    print("  - GET /              : 跨屏输入主页面")
    print("  - GET /send          : 跨屏输入主页面")
    print("  - POST /send         : 复制文本到剪贴板（核心功能）")
    print("  - GET /frontend/*    : 前端静态文件")
    print("  - POST /api/clipboard/copy : 复制文本到剪贴板")
    print("  - POST /api/shortcut/execute : 执行键盘快捷键")
    print("  - POST /api/mouse/execute : 执行鼠标操作")
    print("  - GET /api/mouse/buttons : 获取支持的鼠标按键列表")
    print("  - GET /api/mouse/platform : 获取平台信息和建议")
    print("  - GET /api/mouse-config/list : 获取鼠标按钮列表")
    print("  - POST /api/mouse-config/add : 添加新鼠标按钮")
    print("  - PUT /api/mouse-config/update/{id} : 更新鼠标按钮")
    print("  - DELETE /api/mouse-config/delete/{id} : 删除鼠标按钮")
    print("  - GET /api/mouse-config/get/{id} : 获取单个鼠标按钮")
    print("  - GET /api/button-config/list : 获取按钮列表")
    print("  - POST /api/button-config/add : 添加新按钮")
    print("  - PUT /api/button-config/update/{id} : 更新按钮")
    print("  - DELETE /api/button-config/delete/{id} : 删除按钮")
    print("  - GET /api/button-config/get/{id} : 获取单个按钮")
    print("  - GET /health        : 健康检查")
    print("=" * 60)
    
    # 启动服务器
    # 打包环境下禁用 reload，否则会有问题
    if is_frozen:
        # 打包环境：直接运行 app，不使用 reload
        # 获取SSL上下文
        ssl_context = network_manager.get_ssl_context()
        
        if ssl_context:
            print(f"[INFO] HTTPS已启用，证书文件: {network_manager.config.cert_file}")
            uvicorn.run(app, host="0.0.0.0", port=port, ssl=ssl_context)
        else:
            print("[INFO] 使用HTTP启动服务器")
            uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        # 开发环境：使用 reload 方便调试
        # 获取SSL上下文
        ssl_context = network_manager.get_ssl_context()
        
        if ssl_context:
            print(f"[INFO] HTTPS已启用，证书文件: {network_manager.config.cert_file}")
            uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True, ssl=ssl_context)
        else:
            print("[INFO] 使用HTTP启动服务器")
            uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
