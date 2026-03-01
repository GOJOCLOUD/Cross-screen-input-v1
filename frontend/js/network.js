// 网络请求工具类
// 实现重试机制、超时处理和错误恢复

class NetworkRequest {
    constructor(options = {}) {
        this.defaultOptions = {
            timeout: 30000,        // 默认超时时间 30 秒
            maxRetries: 3,         // 默认最大重试次数
            retryDelay: 1000,       // 默认重试延迟 1 秒
            retryBackoff: 2,       // 重试延迟倍数
            enableRetry: true,      // 是否启用重试
            ...options
        };
        
        // 存储认证令牌
        this.authToken = null;
        
        // 设备ID
        this.deviceId = this.generateDeviceId();
        
        // 心跳检测
        this.heartbeatInterval = null;
        this.heartbeatConfig = {
            interval: 30000,  // 30秒
            timeout: 60000   // 60秒
        };
        
        // 网络状态监听器
        this.statusListeners = [];
        
        // 当前网络状态
        this.isOnline = navigator.onLine;
        
        // 初始化网络状态监听
        this.initNetworkStatusMonitor();
    }
    
    /**
     * 生成设备ID
     */
    generateDeviceId() {
        // 尝试从localStorage获取已存在的设备ID
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
     * 启动心跳检测
     */
    startHeartbeat(deviceName = null) {
        // 清除现有心跳
        this.stopHeartbeat();
        
        // 获取心跳配置
        this.getHeartbeatConfig().then(config => {
            this.heartbeatConfig = config;
            
            // 立即发送一次心跳
            this.sendHeartbeat(deviceName);
            
            // 设置定期心跳
            this.heartbeatInterval = setInterval(() => {
                this.sendHeartbeat(deviceName);
            }, this.heartbeatConfig.interval);
            
            console.log('[NetworkRequest] 心跳检测已启动', {
                deviceId: this.deviceId,
                interval: this.heartbeatConfig.interval
            });
        }).catch(error => {
            console.error('[NetworkRequest] 获取心跳配置失败:', error);
            // 使用默认配置启动心跳
            this.sendHeartbeat(deviceName);
            this.heartbeatInterval = setInterval(() => {
                this.sendHeartbeat(deviceName);
            }, this.heartbeatConfig.interval);
        });
    }
    
    /**
     * 停止心跳检测
     */
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
            console.log('[NetworkRequest] 心跳检测已停止');
        }
    }
    
    /**
     * 获取心跳配置
     */
    async getHeartbeatConfig() {
        try {
            const response = await this.get('/api/heartbeat/config', { timeout: 5000 });
            const config = await response.json();
            return {
                interval: config.interval * 1000,  // 转换为毫秒
                timeout: config.timeout * 1000
            };
        } catch (error) {
            console.error('[NetworkRequest] 获取心跳配置失败:', error);
            return this.heartbeatConfig;
        }
    }
    
    /**
     * 发送心跳
     */
    async sendHeartbeat(deviceName = null) {
        try {
            const response = await this.post('/api/heartbeat/heartbeat', {
                device_id: this.deviceId,
                device_name: deviceName || navigator.userAgent
            }, {
                timeout: this.heartbeatConfig.timeout,
                maxRetries: 1  // 心跳失败不重试，避免网络拥塞
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                console.log('[NetworkRequest] 心跳发送成功');
            } else {
                console.warn('[NetworkRequest] 心跳响应异常:', result);
            }
        } catch (error) {
            console.error('[NetworkRequest] 心跳发送失败:', error);
            // 心跳失败不抛出错误，避免影响用户体验
        }
    }
    
    /**
     * 初始化网络状态监听
     */
    initNetworkStatusMonitor() {
        // 监听网络状态变化
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.notifyStatusChange(true);
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.notifyStatusChange(false);
        });
        
        // 定期检查网络状态
        setInterval(() => {
            this.checkNetworkStatus();
        }, 30000); // 每30秒检查一次
    }
    
    /**
     * 添加网络状态监听器
     */
    addStatusListener(callback) {
        this.statusListeners.push(callback);
        // 立即通知当前状态
        callback(this.isOnline);
    }
    
    /**
     * 移除网络状态监听器
     */
    removeStatusListener(callback) {
        const index = this.statusListeners.indexOf(callback);
        if (index > -1) {
            this.statusListeners.splice(index, 1);
        }
    }
    
    /**
     * 通知状态变化
     */
    notifyStatusChange(isOnline) {
        this.statusListeners.forEach(callback => {
            try {
                callback(isOnline);
            } catch (error) {
                console.error('[NetworkRequest] 状态监听器错误:', error);
            }
        });
    }
    
    /**
     * 检查网络状态
     */
    async checkNetworkStatus() {
        try {
            const response = await this.fetchWithTimeout('/health', {
                method: 'GET',
                timeout: 5000
            }, false); // 不重试
            
            const wasOnline = this.isOnline;
            this.isOnline = response.ok;
            
            if (wasOnline !== this.isOnline) {
                this.notifyStatusChange(this.isOnline);
            }
            
            return this.isOnline;
        } catch (error) {
            if (this.isOnline) {
                this.isOnline = false;
                this.notifyStatusChange(false);
            }
            return false;
        }
    }
    
    /**
     * 设置认证令牌
     */
    setAuthToken(token) {
        this.authToken = token;
        localStorage.setItem('kpsr_auth_token', token);
    }
    
    /**
     * 获取认证令牌
     */
    getAuthToken() {
        if (!this.authToken) {
            this.authToken = localStorage.getItem('kpsr_auth_token');
        }
        return this.authToken;
    }
    
    /**
     * 清除认证令牌
     */
    clearAuthToken() {
        this.authToken = null;
        localStorage.removeItem('kpsr_auth_token');
    }
    
    /**
     * 带超时的fetch请求
     */
    async fetchWithTimeout(url, options = {}, enableRetry = true) {
        const {
            timeout = this.defaultOptions.timeout,
            ...fetchOptions
        } = options;
        
        // 创建超时控制器
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            controller.abort();
        }, timeout);
        
        // 添加认证头
        const token = this.getAuthToken();
        if (token) {
            fetchOptions.headers = {
                ...fetchOptions.headers,
                'Authorization': `Bearer ${token}`
            };
        }
        
        try {
            const response = await fetch(url, {
                ...fetchOptions,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            
            if (error.name === 'AbortError') {
                throw new Error('请求超时');
            }
            
            throw error;
        }
    }
    
    /**
     * 带重试的请求
     */
    async request(url, options = {}) {
        const {
            maxRetries = this.defaultOptions.maxRetries,
            retryDelay = this.defaultOptions.retryDelay,
            retryBackoff = this.defaultOptions.retryBackoff,
            enableRetry = this.defaultOptions.enableRetry && this.defaultOptions.maxRetries > 0,
            ...fetchOptions
        } = options;
        
        let lastError;
        
        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                // 检查网络状态
                if (!this.isOnline) {
                    throw new Error('网络连接不可用');
                }
                
                const response = await this.fetchWithTimeout(url, fetchOptions, false);
                
                // 检查响应状态
                if (!response.ok) {
                    // 如果是认证错误，清除令牌并重新登录
                    if (response.status === 401) {
                        this.clearAuthToken();
                        throw new Error('认证失败，请重新连接');
                    }
                    
                    // 如果是客户端错误，不重试
                    if (response.status >= 400 && response.status < 500) {
                        const errorData = await response.json().catch(() => ({}));
                        throw new Error(errorData.detail || `请求失败: ${response.status}`);
                    }
                    
                    // 服务器错误，可以重试
                    throw new Error(`服务器错误: ${response.status}`);
                }
                
                return response;
            } catch (error) {
                lastError = error;
                
                // 如果是最后一次尝试，直接抛出错误
                if (attempt === maxRetries || !enableRetry) {
                    throw error;
                }
                
                // 计算重试延迟
                const delay = retryDelay * Math.pow(retryBackoff, attempt);
                
                console.warn(`[NetworkRequest] 请求失败，${delay}ms后重试 (${attempt + 1}/${maxRetries}):`, error.message);
                
                // 等待后重试
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
        
        throw lastError;
    }
    
    /**
     * GET请求
     */
    async get(url, options = {}) {
        return this.request(url, {
            method: 'GET',
            ...options
        });
    }
    
    /**
     * POST请求
     */
    async post(url, data, options = {}) {
        return this.request(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            body: JSON.stringify(data),
            ...options
        });
    }
    
    /**
     * PUT请求
     */
    async put(url, data, options = {}) {
        return this.request(url, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            body: JSON.stringify(data),
            ...options
        });
    }
    
    /**
     * DELETE请求
     */
    async delete(url, options = {}) {
        return this.request(url, {
            method: 'DELETE',
            ...options
        });
    }
    
    /**
     * 发送剪贴板数据（带重试和确认）
     */
    async sendClipboardData(text, options = {}) {
        try {
            const response = await this.post('/send', { msg: text }, {
                timeout: 15000,  // 剪贴板操作使用较短超时
                maxRetries: 5,    // 剪贴板操作重试更多次
                ...options
            });
            
            const result = await response.json();
            
            // 确认服务器已接收
            if (result.status !== 'success') {
                throw new Error(result.message || '发送失败');
            }
            
            return result;
        } catch (error) {
            console.error('[NetworkRequest] 发送剪贴板数据失败:', error);
            throw error;
        }
    }
    
    /**
     * 执行快捷键（带重试和确认）
     */
    async executeShortcut(shortcut, options = {}) {
        try {
            const response = await this.post('/api/shortcut/execute', { 
                shortcut: shortcut 
            }, {
                timeout: 10000,  // 快捷键操作使用较短超时
                maxRetries: 3,
                ...options
            });
            
            const result = await response.json();
            
            // 确认操作已执行
            if (result.status !== 'success') {
                throw new Error(result.message || '快捷键执行失败');
            }
            
            return result;
        } catch (error) {
            console.error('[NetworkRequest] 执行快捷键失败:', error);
            throw error;
        }
    }
    
    /**
     * 执行鼠标操作（带重试和确认）
     */
    async executeMouseAction(action, options = {}) {
        try {
            const response = await this.post('/api/mouse/execute', { 
                action: action 
            }, {
                timeout: 10000,  // 鼠标操作使用较短超时
                maxRetries: 3,
                ...options
            });
            
            const result = await response.json();
            
            // 确认操作已执行
            if (result.status !== 'success') {
                throw new Error(result.message || '鼠标操作执行失败');
            }
            
            return result;
        } catch (error) {
            console.error('[NetworkRequest] 执行鼠标操作失败:', error);
            throw error;
        }
    }
}

// 创建全局网络请求实例
window.networkRequest = new NetworkRequest();

// 导出类（用于模块化）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NetworkRequest;
}