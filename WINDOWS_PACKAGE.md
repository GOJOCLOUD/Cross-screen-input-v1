# Windows 打包说明

本指南介绍如何在Windows环境下打包KPSR跨屏输入工具。

## 打包前准备

### 1. 安装Python
- 下载并安装Python 3.8或更高版本
- 安装时勾选"Add Python to PATH"

### 2. 安装Node.js
- 下载并安装Node.js 16或更高版本
- 包含npm包管理器

## 打包步骤

### 方式1：使用一键打包脚本（推荐）

1. 双击运行 `build.bat` 文件
2. 等待脚本自动完成所有步骤
3. 打包完成后，在 `electron/dist/` 目录下找到安装程序

### 方式2：手动打包

#### 第一步：打包Python后端

```powershell
cd backend
pip install -r requirements.txt
pip install pyinstaller
pyinstaller kpsr-backend.spec --clean
```

#### 第二步：打包Electron应用

```powershell
cd ../electron
npm install
npm run build:win
```

## 打包结果

打包完成后，会在 `electron/dist/` 目录下生成以下文件：
- `KPSR跨屏输入-1.0.0-x64.exe` - Windows安装程序

## 注意事项

1. **首次打包**：如果首次打包，请确保所有依赖都已正确安装
2. **杀毒软件**：某些杀毒软件可能会误报，请添加到白名单
3. **管理员权限**：打包过程可能需要管理员权限
4. **网络问题**：如果npm安装缓慢，可以使用国内镜像：
   ```bash
   npm config set registry https://registry.npmmirror.com
   ```

## 故障排除

### 问题1：pyinstaller打包失败
- 确保Python版本兼容（推荐3.9或3.10）
- 更新pip到最新版本：`pip install --upgrade pip`
- 重新安装依赖：`pip install -r requirements.txt --force-reinstall`

### 问题2：Electron打包失败
- 清理npm缓存：`npm cache clean --force`
- 删除node_modules和package-lock.json，重新安装
- 检查Node.js版本是否兼容

### 问题3：运行时错误
- 检查是否安装了所有必要的Visual C++运行库
- 确保目标系统有.NET Framework 4.5或更高版本

## 技术细节

### PyInstaller配置
- 使用 `kpsr-backend.spec` 配置文件
- 包含所有必要的依赖和数据文件
- 生成单文件可执行程序

### Electron Builder配置
- 使用 `electron/package.json` 中的build配置
- 生成NSIS安装程序
- 包含后端可执行文件和前端资源

## 版本管理

- 当前版本：1.0.0
- 版本号在 `electron/package.json` 中定义
- 修改版本号后重新打包会自动更新安装程序版本