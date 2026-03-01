// Electron preload 脚本
// 用于在渲染进程中安全地暴露 API

const { contextBridge, ipcRenderer } = require('electron');

// 暴露给渲染进程的 API
contextBridge.exposeInMainWorld('electronAPI', {
  // 获取平台信息
  getPlatform: () => process.platform,
  
  // 获取应用版本
  getVersion: () => {
    try {
      return require('./package.json').version;
    } catch (e) {
      return '1.0.0';
    }
  },
  
  // 检查是否在 Electron 中运行
  isElectron: () => true,
  
  // 重试启动后端
  retry: () => {
    ipcRenderer.send('retry-start');
  }
});

console.log('KPSR Electron preload 已加载');
