#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器码生成器模块
用于生成基于硬件信息的唯一机器码，不受运行环境影响

在Mac上完成操作
"""

import os
import platform
import hashlib
import subprocess
import re
import uuid
from typing import Optional, List, Dict


def get_cpu_id() -> Optional[str]:
    """
    获取CPU序列号
    Windows: 使用wmic命令
    """
    try:
        if platform.system() == 'Windows':
            cmd = 'wmic cpu get ProcessorId'
            output = subprocess.check_output(cmd, shell=True, text=True)
            # 提取ProcessorId
            for line in output.split('\n'):
                line = line.strip()
                if line and line != 'ProcessorId':
                    return line
        return None
    except Exception:
        return None


def get_motherboard_serial() -> Optional[str]:
    """
    获取主板序列号
    Windows: 使用wmic命令
    """
    try:
        if platform.system() == 'Windows':
            cmd = 'wmic baseboard get SerialNumber'
            output = subprocess.check_output(cmd, shell=True, text=True)
            # 提取SerialNumber
            for line in output.split('\n'):
                line = line.strip()
                if line and line != 'SerialNumber':
                    return line
        return None
    except Exception:
        return None


def get_disk_serial() -> Optional[str]:
    """
    获取硬盘序列号
    Windows: 使用wmic命令
    """
    try:
        if platform.system() == 'Windows':
            cmd = 'wmic diskdrive get SerialNumber'
            output = subprocess.check_output(cmd, shell=True, text=True)
            # 提取第一个非空SerialNumber
            for line in output.split('\n'):
                line = line.strip()
                if line and line != 'SerialNumber':
                    return line
        return None
    except Exception:
        return None


def get_mac_address() -> Optional[str]:
    """
    获取物理网卡MAC地址
    选择第一个非虚拟网卡的MAC地址
    """
    try:
        # 获取所有网络接口的MAC地址
        mac_addresses = []
        
        # 方法1: 使用uuid.getnode()
        try:
            mac = uuid.getnode()
            mac_str = ':'.join([f'{(mac >> 8*i) & 0xff:02x}' for i in range(6)][::-1])
            if not mac_str.startswith('00:00:00:00:00:00'):
                mac_addresses.append(mac_str)
        except Exception:
            pass
        
        # 方法2: 使用系统命令
        if platform.system() == 'Windows':
            cmd = 'getmac /v'
            output = subprocess.check_output(cmd, shell=True, text=True)
            # 解析MAC地址
            for line in output.split('\n'):
                if '本地连接' in line or 'Ethernet' in line or 'Wi-Fi' in line:
                    mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', line)
                    if mac_match:
                        mac = mac_match.group().replace('-', ':')
                        if not mac.startswith('00:00:00:00:00:00'):
                            mac_addresses.append(mac)
        
        # 返回第一个有效的MAC地址
        for mac in mac_addresses:
            # 过滤虚拟网卡MAC地址
            if not (mac.startswith('00:50:56') or mac.startswith('00:0C:29') or 
                   mac.startswith('08:00:27') or mac.startswith('00:05:69')):
                return mac
        
        return None
    except Exception:
        return None


def get_bios_serial() -> Optional[str]:
    """
    获取BIOS序列号
    Windows: 使用wmic命令
    """
    try:
        if platform.system() == 'Windows':
            cmd = 'wmic bios get SerialNumber'
            output = subprocess.check_output(cmd, shell=True, text=True)
            # 提取SerialNumber
            for line in output.split('\n'):
                line = line.strip()
                if line and line != 'SerialNumber':
                    return line
        return None
    except Exception:
        return None


def collect_hardware_info() -> Dict[str, Optional[str]]:
    """
    收集所有可用的硬件信息
    返回一个包含各种硬件ID的字典
    """
    info = {
        'cpu_id': get_cpu_id(),
        'motherboard_serial': get_motherboard_serial(),
        'disk_serial': get_disk_serial(),
        'mac_address': get_mac_address(),
        'bios_serial': get_bios_serial()
    }
    return info


def generate_machine_code(hardware_info: Optional[Dict[str, Optional[str]]] = None) -> str:
    """
    基于硬件信息生成机器码
    
    参数:
        hardware_info: 硬件信息字典，如果为None则自动收集
    
    返回:
        32位的十六进制机器码
    """
    if hardware_info is None:
        hardware_info = collect_hardware_info()
    
    # 过滤掉None值
    valid_info = {k: v for k, v in hardware_info.items() if v is not None}
    
    if not valid_info:
        # 如果无法获取任何硬件信息，使用备用方案
        # 组合多个系统信息
        system_info = f"{platform.system()}-{platform.machine()}-{platform.processor()}"
        unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, system_info))
    else:
        # 按固定顺序组合硬件信息，确保一致性
        ordered_keys = ['cpu_id', 'motherboard_serial', 'disk_serial', 'mac_address', 'bios_serial']
        combined_info = []
        for key in ordered_keys:
            if key in valid_info:
                combined_info.append(valid_info[key])
        
        # 组合所有信息
        combined_str = '|'.join(combined_info)
        
        # 使用SHA256哈希生成机器码
        hash_obj = hashlib.sha256(combined_str.encode('utf-8'))
        unique_id = hash_obj.hexdigest()
    
    # 取前32位作为机器码
    machine_code = unique_id[:32].upper()
    
    # 格式化为XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX
    formatted_code = '-'.join([machine_code[i:i+4] for i in range(0, 32, 4)])
    
    return formatted_code


def get_machine_code() -> str:
    """
    获取当前机器的唯一机器码
    
    这是一个便捷函数，直接收集硬件信息并生成机器码
    
    返回:
        32位的十六进制机器码，格式为XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX
    """
    return generate_machine_code()


def verify_machine_code(machine_code: str) -> bool:
    """
    验证机器码格式是否正确
    
    参数:
        machine_code: 要验证的机器码
    
    返回:
        True如果格式正确，False否则
    """
    # 检查格式: XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX
    pattern = r'^[0-9A-F]{4}(-[0-9A-F]{4}){7}$'
    return bool(re.match(pattern, machine_code))


__all__ = [
    'get_cpu_id',
    'get_motherboard_serial',
    'get_disk_serial',
    'get_mac_address',
    'get_bios_serial',
    'collect_hardware_info',
    'generate_machine_code',
    'get_machine_code',
    'verify_machine_code',
]