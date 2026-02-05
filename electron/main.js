const { app, BrowserWindow, Tray, Menu, dialog, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const http = require('http');
const treeKill = require('tree-kill');

// 保持对窗口和托盘的引用
let mainWindow = null;
let tray = null;
let pythonProcess = null;
const FIXED_PORT = 19653;  // 固定端口
let serverPort = FIXED_PORT;
let isQuitting = false;
let isBackendReady = false;

// 获取资源路径
function getResourcePath(relativePath) {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, relativePath);
  }
  return path.join(__dirname, '..', relativePath);
}

// 获取后端可执行文件路径
function getBackendPath() {
  if (app.isPackaged) {
    // 打包后：使用 extraResources 中的目录模式后端
    const backendName = 'kpsr-backend.exe';
    // 目录模式：Resources/kpsr-backend/kpsr-backend
    const backendPath = path.join(process.resourcesPath, 'kpsr-backend', backendName);
    console.log('打包环境，后端路径:', backendPath);
    console.log('后端文件是否存在:', fs.existsSync(backendPath));
    return backendPath;
  } else {
    // 开发环境：使用 dist 目录下的可执行文件（目录模式）
    const backendName = 'kpsr-backend.exe';
    const backendPath = path.join(__dirname, '..', 'backend', 'dist', 'kpsr-backend', backendName);
    console.log('开发环境，后端路径:', backendPath);
    if (fs.existsSync(backendPath)) {
      return backendPath;
    }
    // 回退：单文件模式路径
    const singleFilePath = path.join(__dirname, '..', 'backend', 'dist', backendName);
    if (fs.existsSync(singleFilePath) && fs.statSync(singleFilePath).isFile()) {
      return singleFilePath;
    }
    return null; // 返回 null 表示需要用 python 运行
  }
}

// 获取加载页面路径
function getLoadingPagePath() {
  if (app.isPackaged) {
    return path.join(__dirname, 'loading.html');
  }
  return path.join(__dirname, 'loading.html');
}

// 更新加载页面状态
function updateLoadingStatus(message) {
  if (mainWindow && mainWindow.webContents) {
    mainWindow.webContents.executeJavaScript(`
      if (typeof updateStatus === 'function') {
        updateStatus('${message}');
      }
    `).catch(() => {});
  }
}

// 显示加载页面错误
function showLoadingError(message) {
  if (mainWindow && mainWindow.webContents) {
    mainWindow.webContents.executeJavaScript(`
      if (typeof showError === 'function') {
        showError('${message.replace(/'/g, "\\'")}');
      }
    `).catch(() => {});
  }
}

// 使用固定端口，不再需要端口文件读取逻辑

// 检查服务器是否就绪（单次检查）
function checkServerOnce(port) {
  return new Promise((resolve) => {
    const req = http.request({
      hostname: '127.0.0.1',
      port: port,
      path: '/health',
      method: 'GET',
      timeout: 500
    }, (res) => {
      resolve(res.statusCode === 200);
    });
    
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
    
    req.end();
  });
}

// 等待服务器就绪
async function waitForServer(port, timeout = 10000) {
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    if (await checkServerOnce(port)) {
      return true;
    }
    await new Promise(r => setTimeout(r, 100));
  }
  
  throw new Error('服务器启动超时');
}

// 启动 Python 后端
async function startPythonBackend() {
  console.log('=== 开始启动 Python 后端 ===');
  
  // 如果后端进程已经在运行，先停止它
  if (pythonProcess && pythonProcess.pid) {
    console.log('检测到已有后端进程在运行，先停止旧进程...');
    await stopPythonBackend();
    // 等待一下确保进程完全停止
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  
  const backendExePath = getBackendPath();
  console.log('后端可执行文件路径:', backendExePath);
  console.log('后端文件是否存在:', fs.existsSync(backendExePath));
  
  // 使用固定端口
  serverPort = FIXED_PORT;
  console.log('使用固定端口:', serverPort);
  
  return new Promise(async (resolve, reject) => {
    // 设置环境变量
    const env = {
      ...process.env,
      PYTHONUNBUFFERED: '1',
      PYTHONIOENCODING: 'utf-8',
      KPSR_PACKAGED: '1' // 标记为打包环境
    };
    
    let spawnCmd, spawnArgs, spawnCwd;
    
    if (backendExePath) {
      // 使用打包后的可执行文件
      console.log('使用打包后端:', backendExePath);
      updateLoadingStatus('正在启动后端服务...');
      
      // 检查文件是否存在
      if (!fs.existsSync(backendExePath)) {
        const errMsg = `后端文件不存在: ${backendExePath}`;
        console.error(errMsg);
        reject(new Error(errMsg));
        return;
      }
      
      // 检查文件权限
      try {
        fs.accessSync(backendExePath, fs.constants.X_OK);
        console.log('后端文件有执行权限');
      } catch (err) {
        console.error('后端文件无执行权限:', err);
      }
      
      spawnCmd = backendExePath;
      spawnArgs = [];
      spawnCwd = path.dirname(backendExePath);
    } else {
      // 开发环境：使用 python3 运行
      const backendPath = getResourcePath('backend');
      const mainPyPath = path.join(backendPath, 'main.py');
      console.log('使用 Python 运行:', mainPyPath);
      updateLoadingStatus('正在启动 Python 后端...');
      
      if (!fs.existsSync(mainPyPath)) {
        const errMsg = `Python 文件不存在: ${mainPyPath}`;
        console.error(errMsg);
        reject(new Error(errMsg));
        return;
      }
      
      spawnCmd = 'python';
      spawnArgs = [mainPyPath];
      spawnCwd = backendPath;
    }
    
    console.log('启动命令:', spawnCmd);
    console.log('启动参数:', spawnArgs);
    console.log('工作目录:', spawnCwd);
    console.log('环境变量:', {
      PYTHONUNBUFFERED: env.PYTHONUNBUFFERED,
      PYTHONIOENCODING: env.PYTHONIOENCODING,
      KPSR_PACKAGED: env.KPSR_PACKAGED
    });
    
    // 启动后端进程
    try {
      console.log('正在启动后端进程...');
      pythonProcess = spawn(spawnCmd, spawnArgs, {
        cwd: spawnCwd,
        env: env,
        stdio: ['pipe', 'pipe', 'pipe']
      });
      console.log('后端进程已启动，PID:', pythonProcess.pid);
    } catch (err) {
      console.error('spawn 失败:', err);
      console.error('错误堆栈:', err.stack);
      reject(err);
      return;
    }
    
    // 监听输出（仅用于日志）
    pythonProcess.stdout.on('data', (data) => {
      console.log('[Backend stdout]', data.toString().trim());
    });
    
    pythonProcess.stderr.on('data', (data) => {
      console.error('[Backend stderr]', data.toString().trim());
    });
    
    pythonProcess.on('error', (err) => {
      console.error('后端进程启动失败:', err);
      console.error('错误堆栈:', err.stack);
      reject(err);
    });
    
    pythonProcess.on('exit', (code, signal) => {
      console.log(`后端进程退出: code=${code}, signal=${signal}`);
      const wasQuitting = isQuitting;
      pythonProcess = null;
      isBackendReady = false;
      
      // 只有在非正常退出且应用未退出时才提示
      // 如果应用正在退出（isQuitting=true），不提示错误
      if (!wasQuitting && !isQuitting) {
        console.log('⚠️ 后端进程意外退出，但应用仍在运行');
        // 不显示错误对话框，因为应用可能只是最小化到后台
        // 用户重新打开窗口时会自动重启后端
      }
    });
    
    // 等待服务器启动
    updateLoadingStatus('等待服务启动...');
    
    try {
      // 使用固定端口，直接等待服务器就绪
      console.log('使用固定端口:', serverPort);
      
      // 等待服务器真正就绪（最多15秒，增加超时时间）
      updateLoadingStatus('正在连接服务...');
      
      // 先等待2秒，让后端有足够的时间启动
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // 检查端口是否被占用
      console.log('检查端口', serverPort, '是否被占用...');
      
      // 等待服务器就绪
      await waitForServer(serverPort, 15000);
      
      console.log('服务器已就绪');
      isBackendReady = true;
      resolve(serverPort);
    } catch (err) {
      console.error('启动失败:', err);
      console.error('错误堆栈:', err.stack);
      
      // 尝试获取更多信息
      if (pythonProcess) {
        console.log('后端进程状态:', {
          pid: pythonProcess.pid,
          killed: pythonProcess.killed,
          exitCode: pythonProcess.exitCode,
          signalCode: pythonProcess.signalCode
        });
      }
      
      reject(err);
    }
  });
}

// 停止 Python 后端（带超时保护）
function stopPythonBackend() {
  return new Promise((resolve) => {
    if (pythonProcess && pythonProcess.pid) {
      console.log('正在停止 Python 进程...');
      const pid = pythonProcess.pid;
      
      // 设置超时，最多等待 2 秒
      const timeout = setTimeout(() => {
        console.log('停止进程超时，强制杀死');
        try {
          process.kill(pid, 'SIGKILL');
        } catch (e) {
          // 进程可能已经不存在
        }
        pythonProcess = null;
        resolve();
      }, 2000);
      
      // 尝试正常终止
      treeKill(pid, 'SIGTERM', (err) => {
        clearTimeout(timeout);
        if (err) {
          console.error('停止进程失败:', err);
          try {
            process.kill(pid, 'SIGKILL');
          } catch (e) {
            // 忽略
          }
        }
        pythonProcess = null;
        resolve();
      });
    } else {
      resolve();
    }
  });
}

// 创建主窗口（先显示加载页面）
function createWindow() {
  // 获取应用图标路径
  const getAppIcon = () => {
    if (app.isPackaged) {
      return path.join(process.resourcesPath, 'icons', 'app-icon.png');
    } else {
      return path.join(__dirname, '..', 'assets', 'icons', 'app-icon.png');
    }
  };

  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: 'KPSR 跨屏输入',
    icon: getAppIcon(),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    show: false,
    backgroundColor: '#e8f4fd' // 与 loading 页面背景色一致（淡蓝色）
  });
  
  // 先加载本地加载页面
  const loadingPath = getLoadingPagePath();
  console.log('加载 loading 页面:', loadingPath);
  mainWindow.loadFile(loadingPath);
  
  // 页面加载完成后显示窗口
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    console.log('窗口已显示，开始启动后端...');
    
    // 窗口显示后立即开始启动后端
    startBackendAndNavigate();
  });
  
  // 处理外部链接
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
  
  // 窗口关闭时的处理
  mainWindow.on('close', (event) => {
    // Windows: 关闭窗口时退出应用
    isQuitting = true;
    // 停止后端进程
    if (pythonProcess) {
      stopPythonBackend();
    }
  });
  
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// 启动后端并导航到主页面
async function startBackendAndNavigate() {
  try {
    console.log('开始启动后端服务...');
    updateLoadingStatus('正在准备启动后端服务...');
    
    // 获取后端路径
    const backendPath = getBackendPath();
    console.log('后端路径:', backendPath);
    console.log('后端文件是否存在:', fs.existsSync(backendPath));
    
    // 启动后端
    await startPythonBackend();
    
    // 后端启动成功，跳转到主页面
    console.log('后端启动成功，跳转到主页面...');
    updateLoadingStatus('服务已就绪，正在加载页面...');
    
    // 稍等一下确保服务完全就绪
    setTimeout(() => {
      if (mainWindow) {
        const mainUrl = `http://127.0.0.1:${serverPort}/`;
        console.log('导航到:', mainUrl);
        mainWindow.loadURL(mainUrl);
      }
    }, 300);
    
  } catch (err) {
    console.error('后端启动失败:', err);
    console.error('错误堆栈:', err.stack);
    showLoadingError(`启动失败: ${err.message}\n\n请尝试重启应用，或检查应用是否完整安装。\n\n详细错误:\n${err.stack}`);
  }
}

// 创建系统托盘
function createTray() {
  // 使用生成的托盘图标
  const iconPath = app.isPackaged 
    ? path.join(process.resourcesPath, 'icons', 'tray-icon.png')
    : path.join(__dirname, '..', 'assets', 'icons', 'tray-icon.png');
  
  // 如果图标不存在，使用空图标
  try {
    tray = new Tray(iconPath);
  } catch (e) {
    // 创建一个简单的 nativeImage 作为后备
    const { nativeImage } = require('electron');
    const emptyIcon = nativeImage.createEmpty();
    tray = new Tray(emptyIcon);
  }
  
  const contextMenu = Menu.buildFromTemplate([
    {
      label: '显示主窗口',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      }
    },
    {
      label: '手机端二维码',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      }
    },
    { type: 'separator' },
    {
      label: '重启服务',
      click: async () => {
        try {
          console.log('用户手动重启服务...');
          isBackendReady = false;
          
          // 先清理端口，再停止后端
          const { exec } = require('child_process');
          const port = FIXED_PORT;
          
          // 清理端口
          if (process.platform === 'win32') {
            exec(`netstat -ano | findstr :${port}`, (err, stdout) => {
              if (!err && stdout) {
                const lines = stdout.split('\n');
                lines.forEach(line => {
                  const parts = line.trim().split(/\s+/);
                  const pid = parts[parts.length - 1];
                  if (pid && pid !== '0') {
                    exec(`taskkill /F /PID ${pid} 2>nul`, () => {});
                  }
                });
              }
            });
          }
          
          await stopPythonBackend();
          
          // 等待一下确保端口释放
          setTimeout(async () => {
            // 先显示加载页面
            if (mainWindow) {
              const loadingPath = getLoadingPagePath();
              mainWindow.show();
              mainWindow.focus();
              mainWindow.loadFile(loadingPath);
              
              // 等待加载页面显示后再启动后端
              setTimeout(() => {
                startBackendAndNavigate();
              }, 300);
            } else {
              startBackendAndNavigate();
            }
          }, 500);
        } catch (err) {
          console.error('重启失败:', err);
          dialog.showErrorBox('重启失败', err.message);
        }
      }
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        isQuitting = true;
        app.quit();
      }
    }
  ]);
  
  tray.setToolTip('KPSR 跨屏输入');
  tray.setContextMenu(contextMenu);
  
  // 点击托盘图标显示窗口
  tray.on('click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.focus();
      } else {
        mainWindow.show();
      }
    }
  });
}

// 注意：重试功能通过页面刷新实现，不再使用 IPC

// 应用准备就绪
app.whenReady().then(() => {
  console.log('应用准备就绪');
  console.log('是否打包环境:', app.isPackaged);
  console.log('资源路径:', process.resourcesPath);
  console.log('应用路径:', app.getAppPath());
  
  // 先创建窗口（显示加载页面），后端启动在窗口显示后进行
  createWindow();
  createTray();
});

// Windows 点击任务栏图标时重新显示窗口
app.on('activate', () => {
  if (mainWindow === null) {
    // 窗口不存在，创建新窗口
    createWindow();
  } else {
    // 如果窗口存在，只显示它，不重启后端
    mainWindow.show();
    mainWindow.focus();
    
    // 检查后端是否还在运行
    if (!pythonProcess || !pythonProcess.pid) {
      // 后端未运行，需要重新启动
      console.log('后端进程未运行，重新启动...');
      isBackendReady = false;
      const loadingPath = getLoadingPagePath();
      if (mainWindow && mainWindow.webContents) {
        mainWindow.loadFile(loadingPath);
        mainWindow.once('ready-to-show', () => {
          startBackendAndNavigate();
        });
      } else {
        startBackendAndNavigate();
      }
    } else {
      // 后端正在运行，直接显示窗口，不重启后端
      console.log('后端进程正在运行，直接显示窗口');
      // 如果窗口已经加载了主页面，直接显示即可
      // 如果还在加载页面，等待加载完成
      if (mainWindow && mainWindow.webContents) {
        const currentURL = mainWindow.webContents.getURL();
        if (currentURL && currentURL.includes('loading.html')) {
          // 还在加载页面，等待加载完成
          console.log('窗口还在加载中，等待加载完成...');
        } else {
          // 已经加载了主页面，直接显示
          console.log('窗口已加载主页面，直接显示');
        }
      }
    }
  }
});

// 所有窗口关闭时（Windows 特有行为）
app.on('window-all-closed', () => {
  // Windows: 关闭窗口时退出应用
  isQuitting = true;
  app.quit();
});

// 应用退出前清理
app.on('before-quit', (event) => {
  if (pythonProcess) {
    event.preventDefault();
    isQuitting = true;
    
    // 异步停止后端，但不阻塞退出
    stopPythonBackend().finally(() => {
      app.quit();
    });
    
    // 最多等 3 秒，超时强制退出
    setTimeout(() => {
      console.log('退出超时，强制退出');
      app.exit(0);
    }, 3000);
  }
});

// 处理未捕获的异常
process.on('uncaughtException', (err) => {
  console.error('未捕获的异常:', err);
});
