// KPSR 电脑端控制台

let qrcode = null;
let refreshTimer = null;

document.addEventListener('DOMContentLoaded', init);

async function init() {
    // 直接初始化，无需密码验证
    await loadAccessInfo();
    await loadStatus();
    initCopyBtn();
    startRefresh();
}

// 加载访问信息
async function loadAccessInfo() {
    try {
        const res = await fetch('/api/desktop/access-info');
        const data = await res.json();
        
        // 检查是否有热点连接
        if (data.hotspot_ip) {
            document.getElementById('linkDisplay').textContent = data.phone_url;
            generateQRCode(data.qrcode_url);
        } else {
            document.getElementById('linkDisplay').textContent = '请先开启电脑热点';
            const qrcodeElement = document.getElementById('qrcode');
            if (qrcodeElement) {
                qrcodeElement.innerHTML = '<p style="color:#999;padding:40px;font-size:14px;">等待热点连接...</p>';
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
        const res = await fetch('/api/desktop/status');
        const data = await res.json();
        
        // 服务器状态
        setStatus('serverDot', 'serverText', data.server_running, '运行中', '已停止');
        
        // 端口
        document.getElementById('portText').textContent = data.port || '--';
        
        // 热点状态 - 使用 hotspot_connected 和 hotspot_ip 判断
        if (data.hotspot_connected && data.hotspot_ip) {
            setStatus('hotspotDot', 'hotspotText', true, data.hotspot_ip, '未连接');
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
    }, 5000);
}


