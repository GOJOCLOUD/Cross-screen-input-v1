// 主入口文件
// 加载所有模块并初始化应用

// 检查API函数是否加载
console.log('[KPSR] main.js 开始加载');
console.log('[KPSR] UIComponents:', typeof window.UIComponents);
console.log('[KPSR] DeviceManager:', typeof window.DeviceManager);
console.log('[KPSR] SettingsManager:', typeof window.SettingsManager);
console.log('[KPSR] ShortcutActions:', typeof window.ShortcutActions);

// 全局变量
let deviceManager = null;
let settingsManager = null;
let shortcutActions = null;
let sidebarManager = null;

// 等待DOM加载完成
document.addEventListener('DOMContentLoaded', async function() {
    Logger.log('DOM加载完成，初始化应用');
    
    // 初始化模块
    await initializeModules();
    
    // 初始化应用
    await initializeApp();
});

// 初始化所有模块
async function initializeModules() {
    // 初始化设备管理器
    deviceManager = new DeviceManager();
    
    // 初始化设置管理器
    settingsManager = new SettingsManager();
    
    // 初始化快捷键操作
    shortcutActions = new ShortcutActions();
    
    Logger.log('所有模块已初始化');
}

// 初始化应用
async function initializeApp() {
    try {
        // 检查设备配对状态
        const pairingStatus = await deviceManager.checkPairingStatus();
        
        if (!pairingStatus.paired) {
            // 设备未配对，跳转到配对页面
            Logger.log('设备未配对，跳转到配对页面');
            window.location.href = '/pair';
            return;
        }
        
        // 设备已配对，初始化应用
        Logger.log('设备已配对，初始化应用');
        
        // 初始化DOM元素引用
        const DOM = getDOMElements();
        
        if (!DOM.input || !DOM.list || !DOM.welcome) {
            Logger.error('DOM元素未找到！');
            UIComponents.showToast('页面加载错误，请刷新重试');
            return;
        }
        
        // 初始化输入框
        initializeInput(DOM);
        
        // 初始化快捷键操作
        await shortcutActions.initialize();
        
        // 初始化侧边栏
        sidebarManager = UIComponents.createSidebar(DOM.sidebar, DOM.overlay, DOM.menuBtn);
        
        // 设置网络状态监听
        window.networkRequest.addStatusListener((isOnline) => {
            if (isOnline) {
                Logger.log('网络已连接');
                UIComponents.showToast('网络已连接', 'success');
            } else {
                Logger.log('网络已断开');
                UIComponents.showToast('网络已断开，请检查网络连接', 'error');
            }
        });
        
        // 页面可见性变化处理
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                // 页面变为可见时，重新启动心跳
                window.networkRequest.startHeartbeat(deviceManager.getDeviceName());
            } else {
                // 页面不可见时，停止心跳以节省资源
                window.networkRequest.stopHeartbeat();
            }
        });
        
        // 页面卸载时停止心跳
        window.addEventListener('beforeunload', () => {
            window.networkRequest.stopHeartbeat();
        });
        
        Logger.log('应用初始化完成');
    } catch (error) {
        Logger.error('应用初始化失败:', error);
        UIComponents.showToast('应用初始化失败: ' + error.message, 'error');
    }
}

// 获取DOM元素
function getDOMElements() {
    return {
        input: document.getElementById('userInput'),
        sendBtn: document.getElementById('sendBtn'),
        list: document.getElementById('messageList'),
        welcome: document.getElementById('welcomeContainer'),
        scroll: document.getElementById('scrollTarget'),
        form: document.getElementById('sendForm'),
        menuBtn: document.getElementById('menuBtn'),
        sidebar: document.getElementById('sidebar'),
        overlay: document.getElementById('overlay')
    };
}

// 初始化输入框
function initializeInput(DOM) {
    // 输入框自动调整高度
    const autoResize = UIComponents.createAutoResize(DOM.input);
    autoResize.init();
    
    // 绑定发送事件
    DOM.form.addEventListener('submit', handleSend);
    DOM.sendBtn.onclick = (e) => {
        e.preventDefault();
        handleSend();
    };
    
    // 回车键发送
    DOM.input.onkeydown = (e) => {
        Logger.log('按键事件:', e.key);
        if (e.key === 'Enter' && !e.shiftKey) {
            Logger.log('Enter键被按下，阻止默认行为');
            e.preventDefault();
            handleSend();
        }
    };
}

// 处理发送
async function handleSend(e) {
    if (e) e.preventDefault();
    
    Logger.log('handleSend被调用');
    const content = DOM.input.value.trim();
    Logger.log('输入内容:', content);
    
    if (!content) {
        Logger.log('内容为空或按钮禁用，退出');
        return;
    }
    
    // 清空输入框
    DOM.input.value = '';
    DOM.input.style.height = 'auto';
    DOM.sendBtn.disabled = true;
    DOM.sendBtn.classList.remove('active');
    
    // 渲染消息
    renderMessage(content);
    
    try {
        Logger.log('发送请求到服务器');
        const result = await window.networkRequest.sendClipboardData(content);
        Logger.log('发送成功:', result);
        
    } catch (error) {
        Logger.error('发送失败:', error);
        UIComponents.showToast('发送失败: ' + error.message, 'error');
    }
}

// 渲染消息
function renderMessage(text) {
    Logger.log('renderMessage被调用，文本:', text);
    
    DOM.welcome.style.display = 'none';
    
    const row = document.createElement('div');
    row.className = 'message-row user';
    
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = text;
    
    bubble.addEventListener('click', function() {
        copyToClipboard(text, this);
    });
    
    row.appendChild(bubble);
    DOM.list.appendChild(row);
    
    DOM.scroll.scrollTo({ top: DOM.scroll.scrollHeight, behavior: 'smooth' });
    
    return row;
}

// 复制到剪贴板
function copyToClipboard(text, element) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
            showCopySuccess(element);
        }).catch(() => {
            fallbackCopy(text, element);
        });
    } else {
        fallbackCopy(text, element);
    }
}

function showCopySuccess(element) {
    const originalBackground = element.style.background;
    element.style.background = '#98FB98';
    setTimeout(() => {
        element.style.background = originalBackground;
    }, 300);
}

function fallbackCopy(text, element) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    textarea.setSelectionRange(0, 99999);
    
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            showCopySuccess(element);
        }
    } catch (err) {
        Logger.error('复制失败:', err);
    }
    
    document.body.removeChild(textarea);
}

// 设置菜单功能
window.goToShortcutSettings = function() {
    sidebarManager.close();
    showSettingsModal('shortcut');
};

window.goToMouseSettings = function() {
    sidebarManager.close();
    showSettingsModal('mouse');
};

// 显示设置模态框
async function showSettingsModal(type) {
    const container = document.createElement('div');
    container.className = 'settings-modal-container';
    
    const settingsInterface = settingsManager.createSettingsInterface(container);
    
    // 添加到页面
    document.body.appendChild(container);
    
    // 显示动画
    setTimeout(() => {
        container.style.opacity = '1';
    }, 10);
    
    // 根据类型切换
    if (type === 'shortcut') {
        settingsInterface.switchToShortcuts();
    } else {
        settingsInterface.switchToMouse();
    }
}

// 导出全局函数（用于向后兼容）
window.showToast = UIComponents.showToast;
window.showConfirmDialog = UIComponents.showConfirmDialog;
window.showModal = UIComponents.showModal;