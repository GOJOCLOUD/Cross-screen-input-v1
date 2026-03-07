#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
激活码生成器工具（服务器端使用）
用于生成软件激活码

在Mac上完成操作
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta

# 添加backend目录到Python路径
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, backend_dir)

from utils.activation import ActivationKeyGenerator


class ActivationCodeGeneratorTool:
    """激活码生成器工具"""
    
    def __init__(self):
        self.generator = ActivationKeyGenerator()
        self.keys_file = 'activation_keys.json'
        self.keys_data = self._load_keys()
    
    def _load_keys(self) -> dict:
        """
        加载密钥数据
        
        返回:
            密钥数据字典
        """
        try:
            if os.path.exists(self.keys_file):
                with open(self.keys_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        
        # 如果文件不存在或加载失败，生成新的密钥对
        return self._generate_and_save_keys()
    
    def _generate_and_save_keys(self) -> dict:
        """
        生成并保存新的密钥对
        
        返回:
            密钥数据字典
        """
        print("正在生成新的RSA密钥对...")
        
        private_key, public_key = self.generator.generate_key_pair()
        private_pem, public_pem = self.generator.serialize_keys(private_key, public_key)
        
        keys_data = {
            'private_key': private_pem,
            'public_key': public_pem,
            'generated_at': int(time.time()),
            'version': '1.0'
        }
        
        # 保存到文件
        with open(self.keys_file, 'w', encoding='utf-8') as f:
            json.dump(keys_data, f, indent=2)
        
        print("密钥对生成完成并已保存")
        return keys_data
    
    def generate_code(self, machine_code: str, expiry_days: int = 365) -> str:
        """
        生成激活码
        
        参数:
            machine_code: 机器码
            expiry_days: 有效天数
            
        返回:
            激活码
        """
        private_key = self.keys_data['private_key'].encode('utf-8')
        activation_code = self.generator.generate_activation_code(
            machine_code, 
            private_key, 
            expiry_days
        )
        return activation_code
    
    def batch_generate(self, machine_codes: list, expiry_days: int = 365) -> dict:
        """
        批量生成激活码
        
        参数:
            machine_codes: 机器码列表
            expiry_days: 有效天数
            
        返回:
            机器码到激活码的映射字典
        """
        results = {}
        for machine_code in machine_codes:
            try:
                activation_code = self.generate_code(machine_code, expiry_days)
                results[machine_code] = {
                    'activation_code': activation_code,
                    'status': 'success',
                    'expiry_date': (datetime.now() + timedelta(days=expiry_days)).strftime('%Y-%m-%d')
                }
            except Exception as e:
                results[machine_code] = {
                    'activation_code': None,
                    'status': 'failed',
                    'error': str(e)
                }
        return results
    
    def export_public_key(self, filename: str = 'public_key.pem'):
        """
        导出公钥到文件
        
        参数:
            filename: 输出文件名
        """
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(self.keys_data['public_key'])
        print(f"公钥已导出到: {filename}")
    
    def show_keys_info(self):
        """显示密钥信息"""
        print("\n" + "=" * 60)
        print("密钥信息")
        print("=" * 60)
        print(f"版本: {self.keys_data.get('version')}")
        print(f"生成时间: {datetime.fromtimestamp(self.keys_data.get('generated_at')).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"密钥文件: {self.keys_file}")
        print("=" * 60)


def main():
    """主函数"""
    print("=" * 60)
    print("KPSR 跨屏输入 - 激活码生成器")
    print("=" * 60)
    
    tool = ActivationCodeGeneratorTool()
    tool.show_keys_info()
    
    while True:
        print("\n请选择操作:")
        print("1. 生成单个激活码")
        print("2. 批量生成激活码")
        print("3. 导出公钥")
        print("4. 重新生成密钥对")
        print("5. 退出")
        
        choice = input("\n请输入选项 (1-5): ").strip()
        
        if choice == '1':
            machine_code = input("请输入机器码: ").strip()
            if not machine_code:
                print("错误: 机器码不能为空")
                continue
            
            try:
                expiry_days = int(input("请输入有效期（天，默认365）: ").strip() or "365")
            except ValueError:
                expiry_days = 365
            
            try:
                activation_code = tool.generate_code(machine_code, expiry_days)
                print(f"\n生成的激活码:")
                print(f"  机器码: {machine_code}")
                print(f"  激活码: {activation_code}")
                print(f"  有效期: {expiry_days} 天")
                print(f"  到期日期: {(datetime.now() + timedelta(days=expiry_days)).strftime('%Y-%m-%d')}")
            except Exception as e:
                print(f"生成失败: {e}")
        
        elif choice == '2':
            print("\n批量生成模式（每行一个机器码，输入空行结束）:")
            machine_codes = []
            while True:
                machine_code = input(f"机器码 #{len(machine_codes)+1}: ").strip()
                if not machine_code:
                    break
                machine_codes.append(machine_code)
            
            if not machine_codes:
                print("错误: 没有输入任何机器码")
                continue
            
            try:
                expiry_days = int(input("请输入有效期（天，默认365）: ").strip() or "365")
            except ValueError:
                expiry_days = 365
            
            results = tool.batch_generate(machine_codes, expiry_days)
            
            print(f"\n批量生成结果:")
            for machine_code, result in results.items():
                if result['status'] == 'success':
                    print(f"  {machine_code}: {result['activation_code']} (到期: {result['expiry_date']})")
                else:
                    print(f"  {machine_code}: 失败 - {result.get('error', '未知错误')}")
        
        elif choice == '3':
            filename = input("请输入输出文件名（默认: public_key.pem）: ").strip() or "public_key.pem"
            tool.export_public_key(filename)
        
        elif choice == '4':
            confirm = input("确认重新生成密钥对？这将使所有现有激活码失效 (yes/no): ").strip().lower()
            if confirm == 'yes':
                tool.keys_data = tool._generate_and_save_keys()
                tool.show_keys_info()
                print("警告: 旧密钥已失效，请重新生成所有激活码")
            else:
                print("已取消")
        
        elif choice == '5':
            print("退出程序")
            break
        
        else:
            print("无效选项，请重新选择")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序已中断")
    except Exception as e:
        print(f"\n程序出错: {e}")
        sys.exit(1)