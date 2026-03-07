#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器码API路由
提供获取机器码的API接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import logging

from ..utils.machine_id import get_machine_code, collect_hardware_info, verify_machine_code

router = APIRouter()
logger = logging.getLogger(__name__)


class MachineCodeResponse(BaseModel):
    """机器码响应模型"""
    machine_code: str
    success: bool
    message: str = ""


class HardwareInfoResponse(BaseModel):
    """硬件信息响应模型"""
    hardware_info: Dict[str, Any]
    success: bool
    message: str = ""


class VerifyCodeRequest(BaseModel):
    """验证机器码请求模型"""
    machine_code: str


class VerifyCodeResponse(BaseModel):
    """验证机器码响应模型"""
    valid: bool
    success: bool
    message: str = ""


@router.get("/machine-code", response_model=MachineCodeResponse)
async def get_machine_code_api():
    """
    获取当前机器的唯一机器码
    
    返回:
        机器码和操作状态
    """
    try:
        machine_code = get_machine_code()
        logger.info(f"Generated machine code: {machine_code}")
        
        return MachineCodeResponse(
            machine_code=machine_code,
            success=True,
            message="Successfully generated machine code"
        )
    except Exception as e:
        logger.error(f"Error generating machine code: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate machine code: {str(e)}")


@router.get("/hardware-info", response_model=HardwareInfoResponse)
async def get_hardware_info_api():
    """
    获取当前机器的硬件信息
    
    返回:
        硬件信息和操作状态
    """
    try:
        hardware_info = collect_hardware_info()
        logger.info("Collected hardware information")
        
        return HardwareInfoResponse(
            hardware_info=hardware_info,
            success=True,
            message="Successfully collected hardware information"
        )
    except Exception as e:
        logger.error(f"Error collecting hardware info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to collect hardware info: {str(e)}")


@router.post("/verify-machine-code", response_model=VerifyCodeResponse)
async def verify_machine_code_api(request: VerifyCodeRequest):
    """
    验证机器码格式是否正确
    
    参数:
        request: 包含要验证的机器码的请求体
    
    返回:
        验证结果和操作状态
    """
    try:
        is_valid = verify_machine_code(request.machine_code)
        message = "Machine code is valid" if is_valid else "Invalid machine code format"
        
        return VerifyCodeResponse(
            valid=is_valid,
            success=True,
            message=message
        )
    except Exception as e:
        logger.error(f"Error verifying machine code: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to verify machine code: {str(e)}")


__all__ = ["router"]