# 软件激活系统使用说明

## 概述

本软件实现了基于RSA非对称加密的激活系统，具有以下安全特性：

- **RSA 2048位非对称加密**：确保激活码无法被伪造
- **多重哈希验证**：SHA256 + SHA384 双重哈希
- **AES-256加密存储**：许可证文件加密存储
- **机器码绑定**：激活码与特定机器绑定
- **有效期控制**：激活码可设置有效期
- **内置公钥**：公钥嵌入程序，不暴露在外部文件中

## 系统架构

### 1. 服务器端（激活码生成器）

**文件**：`activation_generator.py`

用于生成激活码的工具，需要保密：

```bash
python3 activation_generator.py
```

功能：
- 生成单个激活码
- 批量生成激活码
- 导出公钥
- 重新生成密钥对

**密钥文件**：`activation_keys.json`

包含私钥和公钥，**必须严格保密**，不要泄露给用户。

### 2. 客户端（软件本体）

**核心模块**：
- `backend/utils/activation.py` - 激活码验证算法
- `backend/utils/license_manager.py` - 授权状态管理
- `backend/routes/activation.py` - 激活API接口

**前端界面**：
- `frontend/activation.html` - 激活页面

## 使用流程

### 第一步：获取机器码

用户在软件中获取机器码：

1. 访问激活页面：`http://localhost:7553/activation`
2. 页面会自动显示机器码
3. 或使用API：`GET /api/machine-id/machine-code`

### 第二步：生成激活码（服务器端）

使用激活码生成器工具：

```bash
python3 activation_generator.py
```

选择"生成单个激活码"，输入：
- 机器码：用户提供的机器码
- 有效期：天数（默认365天）

工具会生成类似这样的激活码：
```
XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX...
```

### 第三步：激活软件

用户在激活页面输入激活码：

1. 访问：`http://localhost:7553/activation`
2. 输入激活码
3. 点击"激活软件"按钮
4. 激活成功后，所有功能可用

## 功能限制

未激活时，以下功能将**完全不可用**：

- ✗ 剪贴板操作（复制文本到剪贴板）
- ✗ 快捷键执行
- ✗ 鼠标操作
- ✗ 所有核心功能

激活后，所有功能正常使用。

## API接口

### 激活相关

- `POST /api/activation/activate` - 激活软件
- `POST /api/activation/deactivate` - 停用软件
- `GET /api/activation/status` - 获取激活状态
- `GET /api/activation/machine-code` - 获取机器码

### 机器码相关

- `GET /api/machine-id/machine-code` - 获取机器码
- `GET /api/machine-id/hardware-info` - 获取硬件信息
- `POST /api/machine-id/verify-machine-code` - 验证机器码格式

## 安全性说明

### 为什么这个系统安全？

1. **非对称加密**：即使攻击者知道算法，没有私钥也无法生成有效激活码
2. **机器码绑定**：激活码只能在特定机器上使用
3. **多重哈希**：防止激活码被篡改
4. **加密存储**：许可证文件加密存储，无法手动修改
5. **内置公钥**：公钥嵌入程序代码中，无法替换

### 破解难度

- **算法复杂度**：需要理解RSA、AES、SHA256/384等多种加密算法
- **密钥保护**：私钥在服务器端，客户端无法获取
- **代码混淆**：关键逻辑分散在多个模块中
- **运行时检查**：每次操作都验证激活状态

**预估破解难度**：需要5年以上高级加密和逆向工程经验

## 密钥管理

### 生成新密钥对

如果需要重新生成密钥对：

```bash
python3 generate_keys.py
```

这将：
1. 生成新的RSA密钥对
2. 保存到 `activation_keys.json`
3. 显示公钥内容

**重要**：重新生成密钥后，需要：
1. 将新公钥更新到 `backend/utils/activation.py` 中的 `BUILTIN_PUBLIC_KEY`
2. 重新编译/打包软件
3. 所有旧激活码将失效

### 密钥文件保护

`activation_keys.json` 包含私钥，必须：
- 不要上传到公开仓库
- 不要分享给任何人
- 定期备份
- 使用强密码保护存储位置

## 故障排除

### 激活失败

**错误**："Invalid activation code"

可能原因：
- 激活码输入错误
- 激活码已过期
- 激活码与机器码不匹配
- 激活码被篡改

解决方法：
- 重新输入激活码
- 联系软件提供商重新生成激活码

### 机器码变化

**问题**：同一台机器机器码发生变化

可能原因：
- 硬件变更（更换CPU、主板等）
- 系统重装

解决方法：
- 联系软件提供商，提供新旧机器码
- 重新生成激活码

## 技术细节

### 激活码格式

```
XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX...
```

- Base64编码的加密数据
- 包含：机器码、时间戳、有效期、哈希值
- 使用RSA加密AES密钥，AES加密数据

### 许可证文件

位置：
- Windows: `%APPDATA%\KPSR\.license`
- macOS/Linux: `~/.kpsr/.license`

内容：
- 加密的激活信息
- 使用机器码派生的密钥加密
- 无法手动修改

## 开发者注意事项

### 集成激活检查

在需要保护的功能中添加：

```python
from ..utils.license_manager import check_activation

if not check_activation():
    raise HTTPException(
        status_code=403,
        detail="Software not activated. Please activate the software to use this feature."
    )
```

### 测试激活系统

1. 生成测试激活码
2. 在本地测试激活流程
3. 验证功能限制是否生效
4. 测试过期机制

## 许可证文件

MIT License - 可自由使用和修改

## 技术支持

如有问题，请联系软件提供商。