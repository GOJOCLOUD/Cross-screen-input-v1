/**
 * 前端日志捕获模块
 * 拦截所有console输出并发送到后端保存
 */

(function() {
    'use strict';
    
    // 配置
    const LOG_CONFIG = {
        // 是否启用日志捕获
        enabled: true,
        // 后端日志API地址
        apiUrl: '/api/logs/frontend',
        // 批量发送API地址
        batchApiUrl: '/api/logs/frontend/batch',
        // 批量发送的日志数量阈值
        batchSize: 10,
        // 批量发送的时间间隔（毫秒）
        batchInterval: 5000,
        // 是否同时输出到原始console
        preserveOriginal: true,
        // 要捕获的日志级别
        captureLevels: ['log', 'info', 'warn', 'error', 'debug']
    };
    
    // 保存原始console方法
    const originalConsole = {
        log: console.log.bind(console),
        info: console.info.bind(console),
        warn: console.warn.bind(console),
        error: console.error.bind(console),
        debug: console.debug.bind(console)
    };
    
    // 日志缓冲区
    let logBuffer = [];
    let batchTimer = null;
    
    // 级别映射
    const levelMap = {
        'log': 'INFO',
        'info': 'INFO',
        'warn': 'WARNING',
        'error': 'ERROR',
        'debug': 'DEBUG'
    };
    
    /**
     * 格式化日志参数为字符串
     */
    function formatArgs(args) {
        return args.map(arg => {
            if (arg === null) return 'null';
            if (arg === undefined) return 'undefined';
            if (typeof arg === 'object') {
                try {
                    return JSON.stringify(arg, null, 2);
                } catch (e) {
                    return String(arg);
                }
            }
            return String(arg);
        }).join(' ');
    }
    
    /**
     * 发送单条日志到后端
     */
    async function sendLog(level, message, extra = null) {
        if (!LOG_CONFIG.enabled) return;
        
        try {
            const response = await fetch(LOG_CONFIG.apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    level: level,
                    message: message,
                    extra: extra
                })
            });
            
            if (!response.ok) {
                originalConsole.error('[LogCapture] 发送日志失败:', response.status);
            }
        } catch (error) {
            originalConsole.error('[LogCapture] 发送日志出错:', error.message);
        }
    }
    
    /**
     * 批量发送日志到后端
     */
    async function sendBatchLogs() {
        if (!LOG_CONFIG.enabled || logBuffer.length === 0) return;
        
        const logsToSend = [...logBuffer];
        logBuffer = [];
        
        try {
            const response = await fetch(LOG_CONFIG.batchApiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ logs: logsToSend })
            });
            
            if (!response.ok) {
                originalConsole.error('[LogCapture] 批量发送日志失败:', response.status);
                // 发送失败，放回缓冲区
                logBuffer = logsToSend.concat(logBuffer);
            }
        } catch (error) {
            originalConsole.error('[LogCapture] 批量发送日志出错:', error.message);
            // 发送失败，放回缓冲区（最多保留1000条）
            logBuffer = logsToSend.concat(logBuffer).slice(-1000);
        }
    }
    
    /**
     * 添加日志到缓冲区
     */
    function bufferLog(level, message, extra = null) {
        logBuffer.push({
            level: level,
            message: message,
            extra: extra
        });
        
        // 如果达到批量阈值，立即发送
        if (logBuffer.length >= LOG_CONFIG.batchSize) {
            sendBatchLogs();
        }
    }
    
    /**
     * 创建console方法的包装器
     */
    function createWrapper(method) {
        return function(...args) {
            // 输出到原始console
            if (LOG_CONFIG.preserveOriginal) {
                originalConsole[method](...args);
            }
            
            // 捕获并发送到后端
            if (LOG_CONFIG.enabled && LOG_CONFIG.captureLevels.includes(method)) {
                const level = levelMap[method] || 'INFO';
                const message = formatArgs(args);
                
                // 过滤掉LogCapture自己的日志，避免无限循环
                if (!message.includes('[LogCapture]')) {
                    bufferLog(level, message);
                }
            }
        };
    }
    
    /**
     * 初始化日志捕获
     */
    function init() {
        // 替换console方法
        LOG_CONFIG.captureLevels.forEach(method => {
            if (originalConsole[method]) {
                console[method] = createWrapper(method);
            }
        });
        
        // 启动定时批量发送
        batchTimer = setInterval(sendBatchLogs, LOG_CONFIG.batchInterval);
        
        // 页面卸载前发送剩余日志
        window.addEventListener('beforeunload', () => {
            if (logBuffer.length > 0) {
                // 使用同步方式发送（可能不总是成功）
                navigator.sendBeacon(LOG_CONFIG.batchApiUrl, JSON.stringify({ logs: logBuffer }));
            }
        });
        
        // 捕获未处理的错误
        window.addEventListener('error', (event) => {
            const message = `未处理的错误: ${event.message} at ${event.filename}:${event.lineno}:${event.colno}`;
            bufferLog('ERROR', message, {
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                error: event.error ? event.error.stack : null
            });
        });
        
        // 捕获未处理的Promise拒绝
        window.addEventListener('unhandledrejection', (event) => {
            const message = `未处理的Promise拒绝: ${event.reason}`;
            bufferLog('ERROR', message, {
                reason: String(event.reason),
                stack: event.reason && event.reason.stack ? event.reason.stack : null
            });
        });
        
        originalConsole.log('[LogCapture] 日志捕获已启动');
    }
    
    // 暴露控制接口
    window.LogCapture = {
        // 启用/禁用日志捕获
        enable: function() {
            LOG_CONFIG.enabled = true;
            originalConsole.log('[LogCapture] 日志捕获已启用');
        },
        disable: function() {
            LOG_CONFIG.enabled = false;
            originalConsole.log('[LogCapture] 日志捕获已禁用');
        },
        // 获取当前状态
        isEnabled: function() {
            return LOG_CONFIG.enabled;
        },
        // 立即发送缓冲区中的日志
        flush: function() {
            sendBatchLogs();
        },
        // 获取缓冲区大小
        getBufferSize: function() {
            return logBuffer.length;
        },
        // 获取原始console方法
        getOriginalConsole: function() {
            return originalConsole;
        },
        // 手动发送日志
        log: function(level, message, extra) {
            bufferLog(level.toUpperCase(), message, extra);
        }
    };
    
    // DOM加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
