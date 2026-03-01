#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络配置API路由
提供网络配置管理接口
"""

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

# 导入网络配置管理器
from utils.network_config import network_manager
from utils.logger import info, error

# 创建路由器实例
router = APIRouter()

# 请求模型
class AccessModeRequest(BaseModel):
    mode: str  # "private", "lan", "all"

class AuthTokenRequest(BaseModel):
    enabled: bool
    expiry_hours: Optional[int] = 24

class PairDeviceRequest(BaseModel):
    device_id: str
    name: str

class HTTPSRequest(BaseModel):
    enabled: bool
    force_generate: Optional[bool] = False

class OriginRequest(BaseModel):
    origin: str

# 响应模型
class NetworkStatusResponse(BaseModel):
    access_mode: str
    access_mode_description: str
    auth_enabled: bool
    token_expiry: Optional[str]
    paired_devices: List[Dict[str, Any]]
    https_enabled: bool
    cert_info: Optional[Dict[str, Any]] = None
    allowed_origins: List[str]

class HTTPSResponse(BaseModel):
    enabled: bool
    message: str
    cert_info: Optional[Dict[str, Any]] = None

class AuthTokenResponse(BaseModel):
    token: Optional[str]
    expiry: Optional[str]
    enabled: bool

# 获取网络状态
@router.get("/status", response_model=NetworkStatusResponse)
async def get_network_status(request: Request):
    """获取网络配置状态"""
    try:
        config = network_manager.config
        
        # 处理令牌过期时间
        token_expiry = None
        if config.token_expiry:
            token_expiry = config.token_expiry.isoformat()
        
        # 处理配对设备列表
        paired_devices = []
        for device_id, device_info in config.paired_devices.items():
            paired_devices.append({
                "device_id": device_id,
                "name": device_info.get("name", "未知设备"),
                "paired_at": device_info.get("paired_at"),
                "last_seen": device_info.get("last_seen")
            })
        
        # 处理证书信息
        cert_info = None
        if config.https_enabled:
            if config.cert_file and config.key_file:
                cert_info = {
                    "cert_file": config.cert_file,
                    "key_file": config.key_file,
                    "cert_exists": os.path.exists(config.cert_file),
                    "key_exists": os.path.exists(config.key_file)
                }
            else:
                cert_info = {
                    "error": "证书文件路径未配置"
                }
        
        return NetworkStatusResponse(
            access_mode=config.access_mode,
            access_mode_description=network_manager.get_access_mode_description(),
            auth_enabled=config.auth_enabled,
            token_expiry=token_expiry,
            paired_devices=paired_devices,
            https_enabled=config.https_enabled,
            cert_info=cert_info,
            allowed_origins=config.allowed_origins
        )
    except Exception as e:
        error(f"获取网络状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取网络状态失败")

# 设置访问模式
@router.post("/access-mode")
async def set_access_mode(request: AccessModeRequest):
    """设置网络访问模式"""
    try:
        if request.mode not in ["private", "campus", "lan", "all"]:
            raise HTTPException(
                status_code=400,
                detail="无效的访问模式，支持: private, campus, lan, all"
            )
        
        success = network_manager.set_access_mode(request.mode)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="设置访问模式失败"
            )
        
        info(f"访问模式已更新为: {request.mode}")
        
        return {
            "status": "success",
            "message": f"访问模式已更新为: {request.mode}",
            "access_mode": request.mode,
            "description": network_manager.get_access_mode_description()
        }
    except HTTPException:
        raise
    except Exception as e:
        error(f"设置访问模式失败: {e}")
        raise HTTPException(status_code=500, detail="设置访问模式失败")

# 生成验证令牌
@router.post("/auth-token", response_model=AuthTokenResponse)
async def manage_auth_token(request: AuthTokenRequest):
    """管理验证令牌"""
    try:
        if request.enabled:
            # 生成新令牌
            token = network_manager.generate_auth_token(request.expiry_hours)
            expiry = network_manager.config.token_expiry.isoformat()
            
            info(f"验证令牌已生成，过期时间: {expiry}")
            
            return AuthTokenResponse(
                token=token,
                expiry=expiry,
                enabled=True
            )
        else:
            # 禁用验证
            network_manager.config.auth_enabled = False
            network_manager.config.auth_token = None
            network_manager.config.token_expiry = None
            network_manager.save_config()
            
            info("验证令牌已禁用")
            
            return AuthTokenResponse(
                token=None,
                expiry=None,
                enabled=False
            )
    except Exception as e:
        error(f"管理验证令牌失败: {e}")
        raise HTTPException(status_code=500, detail="管理验证令牌失败")

# 配对设备
@router.post("/pair-device")
async def pair_device(request: PairDeviceRequest):
    """配对新设备"""
    try:
        success = network_manager.add_paired_device(
            request.device_id,
            request.name
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="设备配对失败"
            )
        
        info(f"设备已配对: {request.name} ({request.device_id})")
        
        return {
            "status": "success",
            "message": f"设备已配对: {request.name}",
            "device_id": request.device_id,
            "name": request.name
        }
    except HTTPException:
        raise
    except Exception as e:
        error(f"设备配对失败: {e}")
        raise HTTPException(status_code=500, detail="设备配对失败")

# 取消配对设备
@router.delete("/unpair-device/{device_id}")
async def unpair_device(device_id: str):
    """取消设备配对"""
    try:
        success = network_manager.remove_paired_device(device_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="设备未找到"
            )
        
        info(f"设备配对已取消: {device_id}")
        
        return {
            "status": "success",
            "message": "设备配对已取消",
            "device_id": device_id
        }
    except HTTPException:
        raise
    except Exception as e:
        error(f"取消设备配对失败: {e}")
        raise HTTPException(status_code=500, detail="取消设备配对失败")

# 验证设备
@router.post("/verify-device")
async def verify_device(request: PairDeviceRequest, authorization: Optional[str] = Header(None)):
    """验证设备是否已配对"""
    try:
        # 如果启用了身份验证，先验证令牌
        if network_manager.config.auth_enabled:
            if not authorization or not authorization.startswith("Bearer "):
                raise HTTPException(
                    status_code=401,
                    detail="需要提供验证令牌"
                )
            
            token = authorization.split(" ")[1]
            if not network_manager.verify_auth_token(token):
                raise HTTPException(
                    status_code=401,
                    detail="验证令牌无效或已过期"
                )
        
        # 检查设备是否已配对
        is_paired = network_manager.is_device_paired(request.device_id)
        
        if is_paired:
            # 更新最后访问时间
            network_manager.update_device_last_seen(request.device_id)
        
        return {
            "status": "success",
            "paired": is_paired,
            "device_id": request.device_id,
            "name": request.name if is_paired else None
        }
    except HTTPException:
        raise
    except Exception as e:
        error(f"验证设备失败: {e}")
        raise HTTPException(status_code=500, detail="验证设备失败")

# 管理HTTPS设置
@router.post("/https", response_model=HTTPSResponse)
async def manage_https(request: HTTPSRequest):
    """管理HTTPS设置"""
    try:
        if request.enabled:
            # 启用HTTPS
            success = network_manager.enable_https(request.force_generate)
            
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="启用HTTPS失败"
                )
            
            # 获取证书信息
            cert_info = None
            if network_manager.config.cert_file and network_manager.config.key_file:
                cert_info = {
                    "cert_file": network_manager.config.cert_file,
                    "key_file": network_manager.config.key_file,
                    "cert_exists": os.path.exists(network_manager.config.cert_file),
                    "key_exists": os.path.exists(network_manager.config.key_file)
                }
            
            info("HTTPS已启用")
            
            return HTTPSResponse(
                enabled=True,
                message="HTTPS已启用",
                cert_info=cert_info
            )
        else:
            # 禁用HTTPS
            success = network_manager.disable_https()
            
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="禁用HTTPS失败"
                )
            
            info("HTTPS已禁用")
            
            return HTTPSResponse(
                enabled=False,
                message="HTTPS已禁用"
            )
    except HTTPException:
        raise
    except Exception as e:
        error(f"管理HTTPS失败: {e}")
        raise HTTPException(status_code=500, detail="管理HTTPS失败")

# 管理允许的来源
@router.post("/allowed-origins")
async def add_allowed_origin(request: OriginRequest):
    """添加允许的来源"""
    try:
        success = network_manager.add_allowed_origin(request.origin)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="添加来源失败"
            )
        
        info(f"已添加允许的来源: {request.origin}")
        
        return {
            "status": "success",
            "message": f"已添加允许的来源: {request.origin}",
            "allowed_origins": network_manager.config.allowed_origins
        }
    except HTTPException:
        raise
    except Exception as e:
        error(f"添加允许的来源失败: {e}")
        raise HTTPException(status_code=500, detail="添加允许的来源失败")

@router.delete("/allowed-origins/{origin:path}")
async def remove_allowed_origin(origin: str):
    """移除允许的来源"""
    try:
        # URL解码
        from urllib.parse import unquote
        origin = unquote(origin)
        
        success = network_manager.remove_allowed_origin(origin)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="来源未找到"
            )
        
        info(f"已移除允许的来源: {origin}")
        
        return {
            "status": "success",
            "message": f"已移除允许的来源: {origin}",
            "allowed_origins": network_manager.config.allowed_origins
        }
    except HTTPException:
        raise
    except Exception as e:
        error(f"移除允许的来源失败: {e}")
        raise HTTPException(status_code=500, detail="移除允许的来源失败")

@router.get("/allowed-origins")
async def get_allowed_origins():
    """获取允许的来源列表"""
    try:
        return {
            "status": "success",
            "allowed_origins": network_manager.config.allowed_origins,
            "access_mode": network_manager.config.access_mode
        }
    except Exception as e:
        error(f"获取允许的来源失败: {e}")
        raise HTTPException(status_code=500, detail="获取允许的来源失败")