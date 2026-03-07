// 工具函数模块

// 日志工具
const Logger = {
    // 根据环境自动判断：开发环境开启，生产环境关闭
    // 通过检查URL或hostname来判断环境
    DEBUG: (function() {
        // 开发环境：localhost 或 127.0.0.1
        if (typeof window !== 'undefined') {
            const hostname = window.location.hostname;
            return hostname === 'localhost' || hostname === '127.0.0.1';
        }
        return false;
    })(),
    
    log: function(...args) {
        if (this.DEBUG) {
            console.log('[LOG]', ...args);
        }
    },
    
    error: function(...args) {
        console.error('[ERROR]', ...args);  // 错误日志始终输出
    },
    
    warn: function(...args) {
        console.warn('[WARN]', ...args);
    }
};

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 节流函数
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// HTML转义函数，防止XSS攻击
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>'"]/g, m => map[m]);
}

// 输入清理函数
function sanitizeInput(input) {
    if (typeof input !== 'string') return input;
    return escapeHtml(input.trim());
}

// 验证快捷键格式
function validateShortcut(shortcut) {
    if (!shortcut) return { valid: false, message: CONFIG.ERROR_MESSAGES.MISSING_SHORTCUT };
    
    // 先标准化格式
    const normalized = normalizeShortcut(shortcut);
    
    // 检查格式：ctrl+v, alt+tab 等（小写格式）
    if (!CONFIG.REGEX.SHORTCUT.test(normalized)) {
        return { valid: false, message: CONFIG.ERROR_MESSAGES.INVALID_SHORTCUT };
    }
    
    return { valid: true, normalized: normalized };
}

// 标准化快捷键格式：转换为小写，用+分隔
function normalizeShortcut(shortcut) {
    if (!shortcut) return '';
    
    // 去除首尾空格
    shortcut = shortcut.trim();
    
    // 按+分割，转换为小写，重新组合
    const parts = shortcut.split('+').map(part => {
        part = part.trim();
        // 转换为小写
        part = part.toLowerCase();
        return part;
    });
    
    // 重新组合，用+连接
    return parts.join('+');
}

// 显示字段错误
function showFieldError(element, message) {
    // 移除已存在的错误提示
    const existingError = element.nextElementSibling;
    if (existingError && existingError.classList.contains('field-error')) {
        existingError.remove();
    }
    
    // 创建错误提示
    const errorElement = document.createElement('div');
    errorElement.className = 'field-error';
    errorElement.style.color = '#FF3B30';
    errorElement.style.fontSize = '12px';
    errorElement.style.marginTop = '4px';
    errorElement.textContent = message;
    
    element.classList.add('error');
    element.parentNode.appendChild(errorElement);
}

// 隐藏字段错误
function hideFieldError(element) {
    const existingError = element.nextElementSibling;
    if (existingError && existingError.classList.contains('field-error')) {
        existingError.remove();
    }
    element.classList.remove('error');
}

// 显示提示消息
function showToast(message, duration = 3000) {
    // 创建提示元素
    const toast = document.createElement('div');
    toast.style.position = 'fixed';
    toast.style.bottom = '100px';
    toast.style.left = '50%';
    toast.style.transform = 'translateX(-50%)';
    toast.style.padding = '12px 24px';
    toast.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
    toast.style.color = 'white';
    toast.style.borderRadius = '8px';
    toast.style.zIndex = '1000';
    toast.style.fontSize = '14px';
    toast.style.transition = 'all 0.3s ease';
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // 3秒后移除
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, duration);
}

// 生成按钮ID
function generateButtonId() {
    return 'btn_' + Date.now() + '_' + Math.floor(Math.random() * 1000);
}

// 导出工具函数
const Utils = {
    Logger,
    debounce,
    throttle,
    escapeHtml,
    sanitizeInput,
    validateShortcut,
    normalizeShortcut,
    showFieldError,
    hideFieldError,
    showToast,
    generateButtonId
};

// 导出常量
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Utils;
} else if (typeof window !== 'undefined') {
    window.Utils = Utils;
    window.Logger = Logger;
    window.debounce = debounce;
    window.throttle = throttle;
    window.escapeHtml = escapeHtml;
    window.sanitizeInput = sanitizeInput;
    window.validateShortcut = validateShortcut;
    window.normalizeShortcut = normalizeShortcut;
    window.showFieldError = showFieldError;
    window.hideFieldError = hideFieldError;
    window.showToast = showToast;
    window.generateButtonId = generateButtonId;
}
