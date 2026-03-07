#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器码生成器测试脚本
用于验证机器码生成器的稳定性和准确性
"""

import sys
import os

# 添加backend目录到Python路径
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, backend_dir)

from utils.machine_id import (
    get_cpu_id,
    get_motherboard_serial,
    get_disk_serial,
    get_mac_address,
    get_bios_serial,
    collect_hardware_info,
    generate_machine_code,
    get_machine_code,
    verify_machine_code
)


def test_hardware_info_collection():
    """测试硬件信息收集功能"""
    print("=" * 60)
    print("测试硬件信息收集功能")
    print("=" * 60)
    
    # 测试单个硬件信息获取
    print("\n1. 测试单个硬件信息获取:")
    cpu_id = get_cpu_id()
    print(f"   CPU ID: {cpu_id}")
    
    motherboard_serial = get_motherboard_serial()
    print(f"   主板序列号: {motherboard_serial}")
    
    disk_serial = get_disk_serial()
    print(f"   硬盘序列号: {disk_serial}")
    
    mac_address = get_mac_address()
    print(f"   MAC地址: {mac_address}")
    
    bios_serial = get_bios_serial()
    print(f"   BIOS序列号: {bios_serial}")
    
    # 测试收集所有硬件信息
    print("\n2. 测试收集所有硬件信息:")
    hardware_info = collect_hardware_info()
    for key, value in hardware_info.items():
        print(f"   {key}: {value}")
    
    return hardware_info


def test_machine_code_generation(hardware_info):
    """测试机器码生成功能"""
    print("\n" + "=" * 60)
    print("测试机器码生成功能")
    print("=" * 60)
    
    # 使用收集的硬件信息生成机器码
    print("\n1. 使用收集的硬件信息生成机器码:")
    machine_code_1 = generate_machine_code(hardware_info)
    print(f"   机器码: {machine_code_1}")
    
    # 直接生成机器码（内部收集硬件信息）
    print("\n2. 直接生成机器码:")
    machine_code_2 = get_machine_code()
    print(f"   机器码: {machine_code_2}")
    
    # 验证两次生成的机器码是否一致
    print("\n3. 验证一致性:")
    if machine_code_1 == machine_code_2:
        print("   ✓ 两次生成的机器码一致")
    else:
        print("   ✗ 两次生成的机器码不一致")
        print(f"   第一次: {machine_code_1}")
        print(f"   第二次: {machine_code_2}")
    
    # 验证机器码格式
    print("\n4. 验证机器码格式:")
    is_valid = verify_machine_code(machine_code_1)
    if is_valid:
        print("   ✓ 机器码格式正确")
    else:
        print("   ✗ 机器码格式不正确")
    
    return machine_code_1


def test_stability():
    """测试机器码生成器的稳定性"""
    print("\n" + "=" * 60)
    print("测试机器码生成器的稳定性")
    print("=" * 60)
    
    # 多次生成机器码，验证一致性
    print("\n多次生成机器码，验证一致性:")
    machine_codes = []
    for i in range(5):
        code = get_machine_code()
        machine_codes.append(code)
        print(f"   第{i+1}次: {code}")
    
    # 检查是否所有机器码都相同
    all_same = all(code == machine_codes[0] for code in machine_codes)
    if all_same:
        print("\n   ✓ 所有机器码一致，生成器稳定")
    else:
        print("\n   ✗ 机器码不一致，生成器不稳定")
    
    return all_same


def main():
    """主测试函数"""
    print("机器码生成器测试")
    print("测试环境:", sys.platform)
    
    # 测试硬件信息收集
    hardware_info = test_hardware_info_collection()
    
    # 测试机器码生成
    machine_code = test_machine_code_generation(hardware_info)
    
    # 测试稳定性
    is_stable = test_stability()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"生成的机器码: {machine_code}")
    print(f"生成器稳定性: {'稳定' if is_stable else '不稳定'}")
    
    # 保存机器码到文件
    try:
        with open('machine_code.txt', 'w') as f:
            f.write(machine_code)
        print("\n机器码已保存到 machine_code.txt 文件")
    except Exception as e:
        print(f"\n保存机器码失败: {e}")


if __name__ == "__main__":
    main()