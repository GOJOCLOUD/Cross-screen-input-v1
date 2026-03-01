// UI组件模块
// 提供通用的UI组件和交互功能

class UIComponents {
    /**
     * 显示提示消息
     * @param {string} message - 消息内容
     * @param {string} type - 消息类型 (success, error, info)
     * @param {number} duration - 显示时长（毫秒），默认3000ms
     */
    static showToast(message, type = 'info', duration = 3000) {
        // 创建提示元素
        const toast = document.createElement('div');
        toast.className = 'toast';
        
        // 设置样式
        const colors = {
            success: '#34C759',
            error: '#FF3B30',
            info: '#007AFF'
        };
        
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: ${colors[type]};
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            z-index: 1001;
            opacity: 0;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        `;
        
        toast.textContent = message;
        document.body.appendChild(toast);
        
        // 显示动画
        setTimeout(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateX(-50%) translateY(0)';
        }, 10);
        
        // 自动隐藏
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(-50%) translateY(-20px)';
            setTimeout(() => {
                if (document.body.contains(toast)) {
                    document.body.removeChild(toast);
                }
            }, 300);
        }, duration);
    }
    
    /**
     * 显示确认对话框
     * @param {string} message - 确认消息
     * @param {string} confirmText - 确认按钮文本
     * @param {string} cancelText - 取消按钮文本
     * @returns {Promise<boolean>} - 用户是否确认
     */
    static showConfirmDialog(message, confirmText = '确认', cancelText = '取消') {
        return new Promise((resolve) => {
            // 创建遮罩层
            const overlay = document.createElement('div');
            overlay.className = 'confirm-overlay';
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1002;
                opacity: 0;
                transition: opacity 0.3s ease;
            `;
            
            // 创建对话框
            const dialog = document.createElement('div');
            dialog.className = 'confirm-dialog';
            dialog.style.cssText = `
                background: white;
                padding: 24px;
                border-radius: 12px;
                max-width: 400px;
                width: 90%;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
                transform: scale(0.9);
                transition: transform 0.3s ease;
            `;
            
            dialog.innerHTML = `
                <div class="confirm-message">${message}</div>
                <div class="confirm-buttons">
                    <button class="confirm-btn confirm">${confirmText}</button>
                    <button class="confirm-btn cancel">${cancelText}</button>
                </div>
            `;
            
            // 添加样式
            const style = document.createElement('style');
            style.textContent = `
                .confirm-message {
                    margin-bottom: 20px;
                    font-size: 16px;
                    line-height: 1.5;
                    color: #333;
                }
                .confirm-buttons {
                    display: flex;
                    gap: 12px;
                    justify-content: flex-end;
                }
                .confirm-btn {
                    padding: 10px 20px;
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                .confirm-btn.confirm {
                    background: #007AFF;
                    color: white;
                }
                .confirm-btn.confirm:hover {
                    background: #0056CC;
                }
                .confirm-btn.cancel {
                    background: #f0f0f0;
                    color: #333;
                    border: 1px solid #ddd;
                }
                .confirm-btn.cancel:hover {
                    background: #e0e0e0;
                }
            `;
            
            document.head.appendChild(style);
            overlay.appendChild(dialog);
            document.body.appendChild(overlay);
            
            // 显示动画
            setTimeout(() => {
                overlay.style.opacity = '1';
                dialog.style.transform = 'scale(1)';
            }, 10);
            
            // 绑定事件
            const confirmBtn = dialog.querySelector('.confirm-btn.confirm');
            const cancelBtn = dialog.querySelector('.confirm-btn.cancel');
            
            confirmBtn.addEventListener('click', () => {
                cleanup();
                resolve(true);
            });
            
            cancelBtn.addEventListener('click', () => {
                cleanup();
                resolve(false);
            });
            
            // 点击遮罩层关闭
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    cleanup();
                    resolve(false);
                }
            });
            
            // 清理函数
            function cleanup() {
                overlay.style.opacity = '0';
                dialog.style.transform = 'scale(0.9)';
                setTimeout(() => {
                    if (document.body.contains(overlay)) {
                        document.body.removeChild(overlay);
                    }
                    if (document.head.contains(style)) {
                        document.head.removeChild(style);
                    }
                }, 300);
            }
        });
    }
    
    /**
     * 显示加载状态
     * @param {HTMLElement} element - 要显示加载状态的元素
     * @param {string} loadingText - 加载文本
     */
    static showLoading(element, loadingText = '加载中...') {
        if (!element) return;
        
        // 保存原始内容
        const originalContent = element.innerHTML;
        const originalDisabled = element.disabled;
        
        // 设置加载状态
        element.innerHTML = `<span class="loading-spinner"></span>${loadingText}`;
        element.disabled = true;
        element.classList.add('loading');
        
        // 返回恢复函数
        return function hideLoading() {
            element.innerHTML = originalContent;
            element.disabled = originalDisabled;
            element.classList.remove('loading');
        };
    }
    
    /**
     * 创建模态框
     * @param {string} title - 标题
     * @param {string} content - 内容HTML
     * @param {Object} options - 选项
     * @returns {Promise} - 模态框关闭时resolve
     */
    static showModal(title, content, options = {}) {
        return new Promise((resolve) => {
            const {
                width = '90%',
                maxWidth = '500px',
                closeOnOverlay = true,
                showCloseButton = true
            } = options;
            
            // 创建遮罩层
            const overlay = document.createElement('div');
            overlay.className = 'modal-overlay';
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1003;
                opacity: 0;
                transition: opacity 0.3s ease;
            `;
            
            // 创建模态框
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.style.cssText = `
                background: white;
                border-radius: 12px;
                width: ${width};
                max-width: ${maxWidth};
                max-height: 80vh;
                overflow-y: auto;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
                transform: scale(0.9);
                transition: transform 0.3s ease;
            `;
            
            modal.innerHTML = `
                <div class="modal-header">
                    <h3>${title}</h3>
                    ${showCloseButton ? '<button class="modal-close">&times;</button>' : ''}
                </div>
                <div class="modal-content">${content}</div>
            `;
            
            // 添加样式
            const style = document.createElement('style');
            style.textContent = `
                .modal-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 16px 24px;
                    border-bottom: 1px solid #eee;
                }
                .modal-header h3 {
                    margin: 0;
                    font-size: 18px;
                    font-weight: 600;
                    color: #333;
                }
                .modal-close {
                    background: none;
                    border: none;
                    font-size: 24px;
                    color: #999;
                    cursor: pointer;
                    padding: 0;
                    width: 32px;
                    height: 32px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 50%;
                    transition: all 0.2s ease;
                }
                .modal-close:hover {
                    background: #f0f0f0;
                    color: #333;
                }
                .modal-content {
                    padding: 24px;
                }
                .loading-spinner {
                    display: inline-block;
                    width: 16px;
                    height: 16px;
                    border: 2px solid rgba(0, 122, 255, 0.3);
                    border-radius: 50%;
                    border-top-color: #007AFF;
                    animation: spin 1s linear infinite;
                    margin-right: 8px;
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
                .loading {
                    opacity: 0.7;
                }
            `;
            
            document.head.appendChild(style);
            overlay.appendChild(modal);
            document.body.appendChild(overlay);
            
            // 显示动画
            setTimeout(() => {
                overlay.style.opacity = '1';
                modal.style.transform = 'scale(1)';
            }, 10);
            
            // 绑定事件
            const closeBtn = modal.querySelector('.modal-close');
            
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    cleanup();
                });
            }
            
            if (closeOnOverlay) {
                overlay.addEventListener('click', (e) => {
                    if (e.target === overlay) {
                        cleanup();
                    }
                });
            }
            
            // 清理函数
            function cleanup() {
                overlay.style.opacity = '0';
                modal.style.transform = 'scale(0.9)';
                setTimeout(() => {
                    if (document.body.contains(overlay)) {
                        document.body.removeChild(overlay);
                    }
                    if (document.head.contains(style)) {
                        document.head.removeChild(style);
                    }
                    resolve();
                }, 300);
            }
            
            // 返回关闭函数
            return cleanup;
        });
    }
    
    /**
     * 创建侧边栏
     * @param {HTMLElement} sidebar - 侧边栏元素
     * @param {HTMLElement} overlay - 遮罩层元素
     * @param {HTMLElement} menuBtn - 菜单按钮元素
     */
    static createSidebar(sidebar, overlay, menuBtn) {
        return {
            /**
             * 切换侧边栏显示状态
             */
            toggle() {
                const isActive = sidebar.classList.contains('active');
                if (isActive) {
                    this.close();
                } else {
                    this.open();
                }
            },
            
            /**
             * 打开侧边栏
             */
            open() {
                sidebar.classList.add('active');
                overlay.classList.add('active');
                document.body.style.overflow = 'hidden';
            },
            
            /**
             * 关闭侧边栏
             */
            close() {
                sidebar.classList.remove('active');
                overlay.classList.remove('active');
                document.body.style.overflow = '';
            }
        };
    }
    
    /**
     * 创建输入框自动调整高度功能
     * @param {HTMLTextAreaElement} textarea - 输入框元素
     */
    static createAutoResize(textarea) {
        return {
            /**
             * 调整输入框高度
             */
            resize() {
                textarea.style.height = 'auto';
                textarea.style.height = textarea.scrollHeight + 'px';
            },
            
            /**
             * 初始化输入框
             */
            init() {
                // 监听输入事件
                textarea.addEventListener('input', () => {
                    this.resize();
                });
                
                // 监听粘贴事件
                textarea.addEventListener('paste', () => {
                    // 粘贴后稍作延迟再调整高度
                    setTimeout(() => {
                        this.resize();
                    }, 10);
                });
                
                // 初始调整
                this.resize();
            }
        };
    }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UIComponents;
} else {
    window.UIComponents = UIComponents;
}