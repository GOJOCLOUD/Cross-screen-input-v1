# GitHub Actions 自动构建指南

本项目已配置 GitHub Actions，可以自动在 Windows 环境中构建 EXE 文件。

## 触发条件

自动构建会在以下情况触发：
1. 推送到 `main` 分支
2. 发布 Release 时

## 构建流程

1. **环境准备**：设置 Python 3.10 和 Node.js 18
2. **依赖缓存**：缓存 pip 和 npm 依赖以加速构建
3. **安装依赖**：安装 Python 和 Node.js 依赖
4. **资源验证**：检查图标文件是否存在
5. **构建后端**：使用 PyInstaller 打包 Python 后端
6. **构建前端**：使用 electron-builder 打包 Electron 应用
7. **创建发布包**：合并所有构建产物
8. **上传构建产物**：作为 GitHub Actions Artifacts
9. **创建 Release**：如果是 Release 触发，自动创建 GitHub Release

## 获取构建产物

### 方式1：GitHub Actions Artifacts
1. 访问项目的 Actions 页面
2. 点击最新的构建任务
3. 在 Artifacts 部分下载 `KPSR-Windows-EXE`

### 方式2：GitHub Release（推荐）
1. 创建一个新的 Release
2. 构建完成后，Release 中会包含完整的 EXE 文件
3. 直接从 Release 页面下载

## 注意事项

1. **图标文件**：确保 `assets/icons/` 目录下有以下文件：
   - `icon.ico`（主应用图标）
   - `app-icon.png`（Electron 应用图标）

2. **版本管理**：版本号在 `electron/package.json` 中定义

3. **构建时间**：首次构建可能需要 5-10 分钟

4. **缓存**：依赖会被缓存，后续构建会更快

## 故障排除

如果构建失败，请检查：
1. 所有依赖是否正确列在 `requirements.txt` 中
2. 图标文件是否存在于正确位置
3. Python 和 Node.js 版本是否兼容

## 本地构建

如需本地构建，请参考 `WINDOWS_PACKAGE.md` 文档。