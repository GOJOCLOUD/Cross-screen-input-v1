#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
激活API路由
提供激活码验证和状态查询接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from ..utils.license_manager import (
    get_license_manager,
    activate_license,
    deactivate_license,
    get_activation_info,
    check_activation
)
from ..utils.machine_id import get_machine_code

router = APIRouter()
logger = logging.getLogger(__name__)


class ActivationRequest(BaseModel):
    """激活请求模型"""
    activation_code: str


class ActivationResponse(BaseModel):
    """激活响应模型"""
    success: bool
    message: str
    is_activated: bool = False


class DeactivationResponse(BaseModel):
    """停用响应模型"""
    success: bool
    message: str


class ActivationInfoResponse(BaseModel):
    """激活信息响应模型"""
    success: bool
    is_activated: bool
    message: str = ""
    activation_info: Optional[dict] = None


class MachineCodeResponse(BaseModel):
    """机器码响应模型"""
    success: bool
    machine_code: str
    message: str = ""


@router.post("/activate", response_model=ActivationResponse)
async def activate(request: ActivationRequest):
    """
    激活软件
    
    参数:
        request: 包含激活码的请求体
    
    返回:
        激活结果和状态
    """
    try:
        success, message = activate_license(request.activation_code)
        
        if success:
            logger.info(f"Software activated successfully")
            return ActivationResponse(
                success=True,
                message=message,
                is_activated=True
            )
        else:
            logger.warning(f"Activation failed: {message}")
            return ActivationResponse(
                success=False,
                message=message,
                is_activated=False
            )
    except Exception as e:
        logger.error(f"Error during activation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Activation failed: {str(e)}")


@router.post("/deactivate", response_model=DeactivationResponse)
async def deactivate():
    """
    停用软件
    
    返回:
        停用结果和状态
    """
    try:
        success = deactivate_license()
        
        if success:
            logger.info("Software deactivated successfully")
            return DeactivationResponse(
                success=True,
                message="Software deactivated successfully"
            )
        else:
            logger.warning("Deactivation failed")
            return DeactivationResponse(
                success=False,
                message="Deactivation failed"
            )
    except Exception as e:
        logger.error(f"Error during deactivation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Deactivation failed: {str(e)}")


@router.get("/status", response_model=ActivationInfoResponse)
async def get_status():
    """
    获取激活状态
    
    返回:
        激活状态和信息
    """
    try:
        is_activated = check_activation()
        activation_info = get_activation_info() if is_activated else None
        
        message = "Software is activated" if is_activated else "Software is not activated"
        
        return ActivationInfoResponse(
            success=True,
            is_activated=is_activated,
            message=message,
            activation_info=activation_info
        )
    except Exception as e:
        logger.error(f"Error getting activation status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/machine-code", response_model=MachineCodeResponse)
async def get_machine_code_api():
    """
    获取当前机器码
    
    返回:
        机器码和操作状态
    """
    try:
        machine_code = get_machine_code()
        logger.info(f"Generated machine code: {machine_code}")
        
        return MachineCodeResponse(
            success=True,
            machine_code=machine_code,
            message="Machine code generated successfully"
        )
    except Exception as e:
        logger.error(f"Error generating machine code: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate machine code: {str(e)}")


@router.get("/check-feature/{feature_name}")
async def check_feature_access(feature_name: str):
    """
    检查功能访问权限
    
    参数:
        feature_name: 功能名称
    
    返回:
        功能访问权限状态
    """
    try:
        from ..utils.license_manager import check_feature_access
        
        has_access = check_feature_access(feature_name)
        
        return {
            "success": True,
            "feature": feature_name,
            "has_access": has_access,
            "message": f"Feature '{feature_name}' is {'accessible' if has_access else 'not accessible'}"
        }
    except Exception as e:
        logger.error(f"Error checking feature access: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to check feature access: {str(e)}")


__all__ = ["router"]