// 设备管理模块
// 处理设备配对、验证和管理功能

class DeviceManager {
    constructor() {
        this.deviceId = this.getOrCreateDeviceId();
        this.deviceName = this.getDeviceName();
        this.isPaired = false;
        this.authToken = this.getStoredAuthToken();
    }
    
    /**
     * 获取或创建设备ID
     */
    getOrCreateDeviceId() {
        let deviceId = localStorage.getItem('kpsr_device_id');
        if (deviceId) {
            return deviceId;
        }
        
        // 生成新的设备ID
        const timestamp = Date.now().toString(36);
        const random = Math.random().toString(36).substring(2, 15);
        deviceId = `device_${timestamp}_${random}`;
        
        // 保存到localStorage
        localStorage.setItem('kpsr_device_id', deviceId);
        
        return deviceId;
    }
    
    /**
     * 获取设备名称
     */
    getDeviceName() {
        return localStorage.getItem('kpsr_device_name') || this.getDefaultDeviceName();
    }
    
    /**
     * 设置设备名称
     */
    setDeviceName(name) {
        localStorage.setItem('kpsr_device_name', name);
        this.deviceName = name;
    }
    
    /**
     * 获取默认设备名称
     */
    getDefaultDeviceName() {
        const userAgent = navigator.userAgent;
        if (userAgent.includes('iPhone')) return 'iPhone';
        if (userAgent.includes('iPad')) return 'iPad';
        if (userAgent.includes('Android')) return 'Android设备';
        if (userAgent.includes('Windows Phone')) return 'Windows Phone';
        return '移动设备';
    }
    
    /**
     * 获取存储的认证令牌
     */
    getStoredAuthToken() {
        return localStorage.getItem('kpsr_auth_token');
    }
    
    /**
     * 设置认证令牌
     */
    setAuthToken(token) {
        localStorage.setItem('kpsr_auth_token', token);
        this.authToken = token;
    }
    
    /**
     * 清除认证令牌
     */
    clearAuthToken() {
        localStorage.removeItem('kpsr_auth_token');
        this.authToken = null;
    }
    
    /**
     * 检查设备配对状态
     */
    async checkPairingStatus() {
        try {
            const response = await window.networkRequest.post('/api/network/verify-device', {
                device_id: this.deviceId,
                name: this.deviceName
            });
            
            const result = await response.json();
            this.isPaired = result.paired;
            
            return {
                paired: result.paired,
                message: result.message || '',
                deviceInfo: result
            };
        } catch (error) {
            console.error('[DeviceManager] 检查配对状态失败:', error);
            
            // 如果是认证错误，返回未配对
            if (error.message && (error.message.includes('认证') || error.message.includes('401'))) {
                this.isPaired = false;
                return {
                    paired: false,
                    message: '需要重新配对',
                    error: error.message
                };
            }
            
            return {
                paired: false,
                message: '检查配对状态失败',
                error: error.message
            };
        }
    }
    
    /**
     * 生成配对二维码
     */
    generatePairingQR() {
        const pairingData = {
            type: 'pairing_request',
            device_id: this.deviceId,
            device_name: this.deviceName,
            timestamp: Date.now()
        };
        
        return new Promise((resolve, reject) => {
            // 创建canvas元素
            const canvas = document.createElement('canvas');
            
            // 生成二维码
            QRCode.toCanvas(canvas, JSON.stringify(pairingData), {
                width: 200,
                margin: 2,
                color: {
                    dark: '#000000',
                    light: '#ffffff'
                }
            }, function(error) {
                if (error) {
                    console.error('[DeviceManager] 生成二维码失败:', error);
                    reject(error);
                } else {
                    resolve(canvas);
                }
            });
        });
    }
    
    /**
     * 验证令牌
     */
    async verifyToken(token) {
        try {
            // 设置令牌
            this.setAuthToken(token);
            
            // 测试令牌
            const response = await window.networkRequest.get('/api/network/status', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                this.isPaired = true;
                return {
                    success: true,
                    message: '验证成功'
                };
            } else {
                throw new Error('令牌无效');
            }
        } catch (error) {
            console.error('[DeviceManager] 验证令牌失败:', error);
            this.clearAuthToken();
            this.isPaired = false;
            
            return {
                success: false,
                message: error.message || '验证失败',
                error: error
            };
        }
    }
    
    /**
     * 获取设备信息
     */
    getDeviceInfo() {
        return {
            id: this.deviceId,
            name: this.deviceName,
            isPaired: this.isPaired,
            hasToken: !!this.authToken
        };
    }
    
    /**
     * 创建配对界面
     */
    createPairingInterface(container) {
        container.innerHTML = `
            <div class="pairing-container">
                <div class="device-info">
                    <div class="info-item">
                        <label>设备ID</label>
                        <span id="deviceIdDisplay">${this.deviceId}</span>
                    </div>
                    <div class="info-item">
                        <label>设备名称</label>
                        <input type="text" id="deviceNameInput" value="${this.deviceName}" placeholder="例如: 我的手机">
                    </div>
                </div>
                
                <div class="pairing-actions">
                    <button id="startPairingBtn" class="btn primary">
                        <span class="btn-text">开始配对</span>
                    </button>
                </div>
                
                <div id="qrContainer" class="qr-container hidden">
                    <div class="qr-header">
                        <h3>扫描二维码完成配对</h3>
                        <p>请使用电脑端扫描此二维码</p>
                    </div>
                    <div id="qrCanvas" class="qr-canvas"></div>
                </div>
                
                <div id="tokenContainer" class="token-container hidden">
                    <div class="token-header">
                        <h3>输入验证令牌</h3>
                        <p>请输入电脑端显示的验证令牌</p>
                    </div>
                    <div class="token-input">
                        <input type="text" id="tokenInput" placeholder="请输入验证令牌">
                        <button id="verifyTokenBtn" class="btn primary">验证</button>
                    </div>
                </div>
                
                <div id="statusMessage" class="status-message"></div>
            </div>
        `;
        
        // 添加样式
        this.addPairingStyles();
        
        // 绑定事件
        this.bindPairingEvents();
        
        // 返回控制对象
        return {
            updateDeviceName: (name) => {
                this.deviceName = name;
                this.setDeviceName(name);
                document.getElementById('deviceNameInput').value = name;
            },
            showQRCode: () => {
                this.showQRCode();
            },
            showTokenInput: () => {
                this.showTokenInput();
            },
            showStatus: (message, type = 'info') => {
                this.showStatus(message, type);
            },
            getDeviceInfo: () => {
                return this.getDeviceInfo();
            }
        };
    }
    
    /**
     * 添加配对界面样式
     */
    addPairingStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .pairing-container {
                max-width: 400px;
                margin: 0 auto;
                padding: 20px;
            }
            
            .device-info {
                background: rgba(255, 255, 255, 0.9);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }
            
            .info-item {
                margin-bottom: 16px;
            }
            
            .info-item:last-child {
                margin-bottom: 0;
            }
            
            .info-item label {
                display: block;
                font-size: 14px;
                font-weight: 500;
                color: #333;
                margin-bottom: 8px;
            }
            
            .info-item span,
            .info-item input {
                display: block;
                width: 100%;
                padding: 8px 12px;
                border-radius: 6px;
                border: 1px solid #ddd;
                font-size: 14px;
            }
            
            .info-item input {
                background: #f9f9f9;
                transition: border-color 0.2s ease;
            }
            
            .info-item input:focus {
                outline: none;
                border-color: #007AFF;
                box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1);
            }
            
            .pairing-actions {
                text-align: center;
                margin-bottom: 20px;
            }
            
            .btn {
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
                -webkit-tap-highlight-color: transparent;
            }
            
            .btn.primary {
                background: #007AFF;
                color: white;
            }
            
            .btn.primary:hover {
                background: #0056CC;
            }
            
            .btn.primary:active {
                transform: scale(0.98);
            }
            
            .btn.loading {
                opacity: 0.7;
                cursor: not-allowed;
            }
            
            .qr-container,
            .token-container {
                background: rgba(255, 255, 255, 0.9);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                text-align: center;
            }
            
            .qr-header,
            .token-header {
                margin-bottom: 16px;
            }
            
            .qr-header h3,
            .token-header h3 {
                font-size: 18px;
                font-weight: 600;
                color: #333;
                margin-bottom: 8px;
            }
            
            .qr-header p,
            .token-header p {
                font-size: 14px;
                color: #666;
                margin: 0;
            }
            
            .qr-canvas {
                margin: 0 auto;
            }
            
            .token-input {
                display: flex;
                gap: 12px;
                margin-top: 16px;
            }
            
            .token-input input {
                flex: 1;
                padding: 12px;
                border-radius: 6px;
                border: 1px solid #ddd;
                font-size: 14px;
            }
            
            .token-input input:focus {
                outline: none;
                border-color: #007AFF;
                box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1);
            }
            
            .status-message {
                padding: 12px;
                border-radius: 8px;
                text-align: center;
                font-size: 14px;
                font-weight: 500;
                margin-top: 16px;
            }
            
            .status-message.success {
                background: rgba(52, 199, 89, 0.1);
                color: #34C759;
            }
            
            .status-message.error {
                background: rgba(255, 59, 48, 0.1);
                color: #FF3B30;
            }
            
            .status-message.info {
                background: rgba(0, 122, 255, 0.1);
                color: #007AFF;
            }
            
            .hidden {
                display: none !important;
            }
        `;
        
        document.head.appendChild(style);
    }
    
    /**
     * 绑定配对界面事件
     */
    bindPairingEvents() {
        const startPairingBtn = document.getElementById('startPairingBtn');
        const deviceNameInput = document.getElementById('deviceNameInput');
        const verifyTokenBtn = document.getElementById('verifyTokenBtn');
        const tokenInput = document.getElementById('tokenInput');
        
        // 开始配对按钮
        startPairingBtn.addEventListener('click', async () => {
            const deviceName = deviceNameInput.value.trim();
            
            if (!deviceName) {
                this.showStatus('请输入设备名称', 'error');
                return;
            }
            
            this.updateDeviceName(deviceName);
            this.setButtonLoading(startPairingBtn, true);
            
            try {
                const result = await this.checkPairingStatus();
                
                if (result.paired) {
                    this.showStatus('设备已配对，正在跳转...', 'success');
                    setTimeout(() => {
                        window.location.href = '/phone';
                    }, 2000);
                } else {
                    this.showQRCode();
                    this.showStatus(result.message || '请扫描二维码或在电脑上确认配对', 'info');
                }
            } catch (error) {
                this.showStatus('配对失败: ' + error.message, 'error');
            } finally {
                this.setButtonLoading(startPairingBtn, false);
            }
        });
        
        // 验证令牌按钮
        verifyTokenBtn.addEventListener('click', async () => {
            const token = tokenInput.value.trim();
            
            if (!token) {
                this.showStatus('请输入验证令牌', 'error');
                return;
            }
            
            this.setButtonLoading(verifyTokenBtn, true);
            
            try {
                const result = await this.verifyToken(token);
                
                if (result.success) {
                    this.showStatus('验证成功，正在跳转...', 'success');
                    setTimeout(() => {
                        window.location.href = '/phone';
                    }, 2000);
                } else {
                    this.showStatus(result.message, 'error');
                }
            } catch (error) {
                this.showStatus('验证失败: ' + error.message, 'error');
            } finally {
                this.setButtonLoading(verifyTokenBtn, false);
            }
        });
        
        // 设备名称输入框变化事件
        deviceNameInput.addEventListener('input', () => {
            this.updateDeviceName(deviceNameInput.value);
        });
    }
    
    /**
     * 显示二维码
     */
    async showQRCode() {
        const qrContainer = document.getElementById('qrContainer');
        const qrCanvas = document.getElementById('qrCanvas');
        
        try {
            const canvas = await this.generatePairingQR();
            qrCanvas.appendChild(canvas);
            qrContainer.classList.remove('hidden');
        } catch (error) {
            console.error('[DeviceManager] 生成二维码失败:', error);
            this.showStatus('生成二维码失败', 'error');
        }
    }
    
    /**
     * 显示令牌输入
     */
    showTokenInput() {
        const tokenContainer = document.getElementById('tokenContainer');
        const qrContainer = document.getElementById('qrContainer');
        
        qrContainer.classList.add('hidden');
        tokenContainer.classList.remove('hidden');
    }
    
    /**
     * 显示状态消息
     */
    showStatus(message, type = 'info') {
        const statusElement = document.getElementById('statusMessage');
        statusElement.textContent = message;
        statusElement.className = `status-message ${type}`;
        statusElement.classList.remove('hidden');
    }
    
    /**
     * 设置按钮加载状态
     */
    setButtonLoading(button, loading) {
        const btnText = button.querySelector('.btn-text');
        
        if (loading) {
            button.classList.add('loading');
            btnText.innerHTML = '<span class="loading-spinner"></span>处理中...';
            button.disabled = true;
        } else {
            button.classList.remove('loading');
            btnText.textContent = button.id === 'startPairingBtn' ? '开始配对' : '验证';
            button.disabled = false;
        }
    }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DeviceManager;
} else {
    window.DeviceManager = DeviceManager;
}