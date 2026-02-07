@echo off
REM KPSR Windows打包脚本 - APPX版本

setlocal enabledelayedexpansion

echo ========================================
echo KPSR 跨屏输入 - Windows APPX打包脚本
echo ========================================
echo.

REM 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM 第一步：打包Python后端
echo [1/2] 正在打包Python后端...
echo.

cd backend

REM 检查是否安装了pyinstaller
where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到pyinstaller，请先安装：
    echo   pip install pyinstaller
    pause
    exit /b 1
)

REM 检查是否安装了所需依赖
echo 检查Python依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖...
    pip install -r requirements.txt
)

REM 清理旧的打包文件
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

REM 使用spec文件打包
echo 开始打包后端...
pyinstaller kpsr-backend.spec --clean

REM 检查打包结果
if not exist "dist\kpsr-backend\kpsr-backend.exe" (
    echo 错误: Python后端打包失败
    pause
    exit /b 1
)

echo ✅ Python后端打包成功
echo.

REM 第二步：安装Electron依赖并打包
echo [2/2] 正在打包Electron应用...
echo.

cd "%SCRIPT_DIR%\electron"

REM 检查是否安装了Node.js
where node >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Node.js，请先安装Node.js
    pause
    exit /b 1
)

REM 安装依赖
echo 安装Electron依赖...
call npm install
if errorlevel 1 (
    echo 错误: Electron依赖安装失败
    pause
    exit /b 1
)

echo ✅ Electron依赖安装完成
echo.

REM 打包Electron应用
echo 开始打包Electron应用...
call npm run build:win
if errorlevel 1 (
    echo 错误: Electron应用打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ 打包完成！
echo ========================================
echo.
echo 打包文件位于: electron\dist\
echo.

REM 列出打包结果
dir /b electron\dist\*.appx 2>nul
if errorlevel 1 (
    echo 未找到.appx文件
) else (
    echo.
    echo 提示：
    echo - Windows: 双击.appx文件安装应用
    echo - 如果提示"无法安装此应用"，需要在Windows设置中启用"旁加载应用"
)

pause