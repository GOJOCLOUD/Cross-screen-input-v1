// KPSR 电脑端控制台

let qrcode = null;
let refreshTimer = null;

document.addEventListener('DOMContentLoaded', init);

async function init() {
    // 直接初始化，无需密码验证
    await loadAccessInfo();
    await loadStatus();
    await loadDevices();
    initCopyBtn();
    initDeviceManagement();
    startRefresh();
}

// 加载设备列表
async function loadDevices() {
    try {
        const res = await window.networkRequest.get('/api/heartbeat/status');
        const data = await res.json();
        
        const deviceList = document.getElementById('deviceList');
        
        if (data.active_connections === 0) {
            deviceList.innerHTML = '<div class="empty-state"><p>暂无已连接的设备</p></div>';
            return;
        }
        
        let html = '';
        for (const [deviceId, deviceInfo] of Object.entries(data.devices)) {
            const statusClass = deviceInfo.status === 'online' ? 'online' : 'offline';
            const statusText = deviceInfo.status === 'online' ? '在线' : '离线';
            const deviceName = deviceInfo.name || '未知设备';
            
            html += `
                <div class="device-item">
                    <div class="device-info">
                        <div class="device-name">${deviceName}</div>
                        <div class="device-id">${deviceId}</div>
                    </div>
                    <div class="device-status">
                        <span class="status-dot ${statusClass}"></span>
                        <span>${statusText}</span>
                    </div>
                </div>
            `;
        }
        
        deviceList.innerHTML = html;
    } catch (e) {
        console.error('加载设备列表失败:', e);
        const deviceList = document.getElementById('deviceList');
        deviceList.innerHTML = '<div class="empty-state"><p>加载失败，请刷新重试</p></div>';
    }
}

// 初始化设备管理
function initDeviceManagement() {
    // 生成验证令牌按钮
    document.getElementById('generateTokenBtn').addEventListener('click', async () => {
        try {
            const res = await window.networkRequest.post('/api/network/auth-token', {
                enabled: true,
                expiry_hours: 24
            });
            
            const data = await res.json();
            
            if (data.enabled && data.token) {
                // 显示令牌
                const token = data.token;
                const message = `验证令牌已生成:\n\n${token}\n\n请将此令牌输入到移动设备中`;
                
                // 创建一个模态框显示令牌
                const modal = document.createElement('div');
                modal.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 1000;
                `;
                
                const content = document.createElement('div');
                content.style.cssText = `
                    background: white;
                    padding: 24px;
                    border-radius: 8px;
                    max-width: 400px;
                    width: 90%;
                    text-align: center;
                `;
                
                content.innerHTML = `
                    <h3 style="margin-bottom: 16px;">验证令牌</h3>
                    <div style="
                        background: #f5f5f5;
                        padding: 12px;
                        border-radius: 4px;
                        font-family: monospace;
                        word-break: break-all;
                        margin-bottom: 16px;
                    ">${token}</div>
                    <button class="button primary" style="margin-right: 8px;">复制令牌</button>
                    <button class="button">关闭</button>
                `;
                
                modal.appendChild(content);
                document.body.appendChild(modal);
                
                // 绑定事件
                content.querySelector('button.primary').addEventListener('click', () => {
                    navigator.clipboard.writeText(token).then(() => {
                        showToast('令牌已复制到剪贴板');
                    });
                });
                
                content.querySelector('button:not(.primary)').addEventListener('click', () => {
                    document.body.removeChild(modal);
                });
                
                modal.addEventListener('click', (e) => {
                    if (e.target === modal) {
                        document.body.removeChild(modal);
                    }
                });
            } else {
                showToast('生成令牌失败', 'error');
            }
        } catch (e) {
            console.error('生成令牌失败:', e);
            showToast('生成令牌失败: ' + e.message, 'error');
        }
    });
    
    // 刷新设备列表按钮
    document.getElementById('refreshDevicesBtn').addEventListener('click', () => {
        loadDevices();
    });
}

// 显示提示消息
function showToast(message, type = 'info') {
    // 创建提示元素
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 4px;
        color: white;
        font-size: 14px;
        z-index: 1001;
        opacity: 0;
        transform: translateY(-20px);
        transition: all 0.3s ease;
    `;
    
    // 设置背景色
    if (type === 'success') {
        toast.style.background = '#34C759';
    } else if (type === 'error') {
        toast.style.background = '#FF3B30';
    } else {
        toast.style.background = '#007AFF';
    }
    
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // 显示动画
    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    }, 10);
    
    // 自动隐藏
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-20px)';
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

// 加载访问信息
async function loadAccessInfo() {
    try {
        const res = await window.networkRequest.get('/api/desktop/access-info');
        const data = await res.json();
        
        // 检查是否有网络连接
        if (data.network_ip) {
            document.getElementById('linkDisplay').textContent = data.phone_url;
            generateQRCode(data.qrcode_url);
        } else {
            document.getElementById('linkDisplay').textContent = '请检查网络连接';
            const qrcodeElement = document.getElementById('qrcode');
            if (qrcodeElement) {
                qrcodeElement.innerHTML = '<p style="color:#999;padding:40px;font-size:14px;">等待网络连接...</p>';
            }
        }
    } catch (e) {
        const linkDisplay = document.getElementById('linkDisplay');
        if (linkDisplay) {
            linkDisplay.textContent = '获取失败';
        }
        console.error('加载访问信息失败:', e);
    }
}

// 生成二维码
function generateQRCode(url) {
    const container = document.getElementById('qrcode');
    container.innerHTML = '';
    
    try {
        qrcode = new QRCode(container, {
            text: url,
            width: 180,
            height: 180,
            colorDark: '#000',
            colorLight: '#fff',
            correctLevel: QRCode.CorrectLevel.M
        });
    } catch (e) {
        container.innerHTML = '<p style="color:#999;padding:40px;">二维码生成失败</p>';
        console.error('二维码生成失败:', e);
    }
}

// 加载状态
async function loadStatus() {
    try {
        const res = await window.networkRequest.get('/api/desktop/status');
        const data = await res.json();
        
        // 服务器状态
        setStatus('serverDot', 'serverText', data.server_running, '运行中', '已停止');
        
        // 端口
        document.getElementById('portText').textContent = data.port || '--';
        
        // 网络状态 - 使用 network_connected 和 network_ip 判断
        if (data.network_connected && data.network_ip) {
            setStatus('hotspotDot', 'hotspotText', true, data.network_ip, '未连接');
        } else {
            setStatus('hotspotDot', 'hotspotText', false, '', '未连接');
        }
        
        // 鼠标监听
        setStatus('mouseDot', 'mouseText', data.mouse_listener_status, '运行中', '已停止');
        
    } catch (e) {
        console.error('加载状态失败:', e);
    }
}

// 设置状态显示
function setStatus(dotId, textId, isOnline, onlineText, offlineText) {
    const dot = document.getElementById(dotId);
    const text = document.getElementById(textId);
    
    if (dot) {
        dot.className = 'status-dot ' + (isOnline ? 'online' : 'offline');
    }
    if (text) {
        text.textContent = isOnline ? onlineText : offlineText;
    }
}

// 初始化复制按钮
function initCopyBtn() {
    const btn = document.getElementById('copyBtn');
    const feedback = document.getElementById('copyFeedback');
    
    if (!btn) return;
    
    btn.addEventListener('click', async () => {
        const text = document.getElementById('linkDisplay').textContent;
        if (!text || text === '获取中...' || text === '获取失败') return;
        
        try {
            await navigator.clipboard.writeText(text);
            showFeedback();
        } catch (e) {
            // 降级方案
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.style.cssText = 'position:fixed;left:-9999px';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            showFeedback();
        }
    });
    
    function showFeedback() {
        if (feedback) {
            feedback.classList.add('show');
            setTimeout(() => feedback.classList.remove('show'), 1500);
        }
    }
}

// 页面隐藏时停止刷新
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        if (refreshTimer) {
            clearInterval(refreshTimer);
            refreshTimer = null;
        }
    } else {
        // 页面重新可见时刷新状态
        loadStatus();
        loadAccessInfo();
        loadNetworkConfig();
        startRefresh();
    }
});

// 页面卸载时清理定时器
window.addEventListener('beforeunload', () => {
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }
});

window.addEventListener('pagehide', () => {
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }
});

// 定时刷新状态
function startRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    refreshTimer = setInterval(() => {
        loadStatus();
        loadAccessInfo();
        loadDevices();
        loadNetworkConfig();
    }, 5000);
}

// 网络配置相关功能
async function loadNetworkConfig() {
    try {
        const res = await window.networkRequest.get('/api/network/status');
        const data = res.data;
        
        // 设置当前访问模式
        const accessModeSelect = document.getElementById('accessMode');
        if (accessModeSelect && data.access_mode) {
            accessModeSelect.value = data.access_mode;
        }
        
        // 更新描述
        updateAccessModeDescription(data.access_mode);
        
    } catch (e) {
        console.error('加载网络配置失败:', e);
    }
}

function updateAccessModeDescription(mode) {
    const descriptions = {
        'private': '私有网络访问 (仅限10.x.x.x, 172.16.x.x-172.31.x.x, 192.168.x.x)',
        'campus': '校园网访问 (包含私有网络和常见校园网IP段)',
        'lan': '局域网访问 (包含所有私有网络范围)',
        'all': '所有网络访问 (不限制IP地址)'
    };
    
    const descElement = document.getElementById('accessModeDescription');
    if (descElement) {
        descElement.textContent = descriptions[mode] || '未知模式';
    }
}

async function saveNetworkConfig() {
    try {
        const accessMode = document.getElementById('accessMode').value;
        
        const res = await window.networkRequest.post('/api/network/access-mode', {
            mode: accessMode
        });
        
        if (res.status === 'success') {
            // 更新描述
            updateAccessModeDescription(accessMode);
            
            // 显示成功消息
            showMessage('网络配置已保存', 'success');
        } else {
            showMessage('保存网络配置失败', 'error');
        }
        
    } catch (e) {
        console.error('保存网络配置失败:', e);
        showMessage('保存网络配置失败: ' + e.message, 'error');
    }
}

function showMessage(message, type = 'info') {
    // 创建消息元素
    const messageEl = document.createElement('div');
    messageEl.className = `message message-${type}`;
    messageEl.textContent = message;
    
    // 添加样式
    messageEl.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 4px;
        color: white;
        font-size: 14px;
        z-index: 1000;
        max-width: 300px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        opacity: 0;
        transform: translateY(-20px);
        transition: all 0.3s ease;
    `;
    
    // 设置背景色
    if (type === 'success') {
        messageEl.style.backgroundColor = '#4CAF50';
    } else if (type === 'error') {
        messageEl.style.backgroundColor = '#F44336';
    } else {
        messageEl.style.backgroundColor = '#2196F3';
    }
    
    // 添加到页面
    document.body.appendChild(messageEl);
    
    // 显示动画
    setTimeout(() => {
        messageEl.style.opacity = '1';
        messageEl.style.transform = 'translateY(0)';
    }, 10);
    
    // 3秒后自动消失
    setTimeout(() => {
        messageEl.style.opacity = '0';
        messageEl.style.transform = 'translateY(-20px)';
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.parentNode.removeChild(messageEl);
            }
        }, 300);
    }, 3000);
}

// 初始化网络配置
document.addEventListener('DOMContentLoaded', () => {
    // 加载网络配置
    loadNetworkConfig();
    
    // 绑定保存按钮事件
    const saveBtn = document.getElementById('saveNetworkConfig');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveNetworkConfig);
    }
    
    // 绑定访问模式变更事件
    const accessModeSelect = document.getElementById('accessMode');
    if (accessModeSelect) {
        accessModeSelect.addEventListener('change', (e) => {
            updateAccessModeDescription(e.target.value);
        });
    }
});


