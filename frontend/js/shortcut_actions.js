// 快捷键操作模块
// 处理快捷键和鼠标操作的执行

class ShortcutActions {
    constructor() {
        this.buttons = [];
        this.shortcutBar = null;
        this.isInitialized = false;
    }
    
    /**
     * 初始化快捷键操作
     */
    async initialize() {
        if (this.isInitialized) return;
        
        try {
            // 加载按钮配置
            await this.loadButtons();
            
            // 获取快捷键栏元素
            this.shortcutBar = document.getElementById('shortcutBar');
            
            if (!this.shortcutBar) {
                console.error('[ShortcutActions] 找不到快捷键栏元素');
                return;
            }
            
            // 渲染按钮
            this.renderButtons();
            
            // 绑定事件
            this.bindEvents();
            
            this.isInitialized = true;
            console.log('[ShortcutActions] 快捷键操作已初始化');
        } catch (error) {
            console.error('[ShortcutActions] 初始化失败:', error);
        }
    }
    
    /**
     * 加载按钮配置
     */
    async loadButtons() {
        try {
            const response = await window.networkRequest.get('/api/button-config/list');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.buttons = data.buttons || [];
                console.log(`[ShortcutActions] 已加载 ${this.buttons.length} 个快捷键按钮`);
            } else {
                console.error('[ShortcutActions] 加载按钮失败:', data);
            }
        } catch (error) {
            console.error('[ShortcutActions] 加载按钮出错:', error);
        }
    }
    
    /**
     * 渲染按钮
     */
    renderButtons() {
        if (!this.shortcutBar) return;
        
        if (this.buttons.length === 0) {
            this.shortcutBar.innerHTML = '';
            this.shortcutBar.style.display = 'none';
            return;
        }
        
        this.shortcutBar.style.display = 'flex';
        
        let html = '';
        this.buttons.forEach(button => {
            html += this.createButtonHTML(button);
        });
        
        this.shortcutBar.innerHTML = html;
    }
    
    /**
     * 创建按钮HTML
     */
    createButtonHTML(button) {
        const icon = this.getButtonIcon(button);
        const typeClass = this.getButtonTypeClass(button.type);
        
        return `
            <button class="shortcut-button ${typeClass}" data-id="${button.id}" data-type="${button.type}">
                <div class="shortcut-button-icon">${icon}</div>
                <div class="shortcut-button-name">${button.name}</div>
            </button>
        `;
    }
    
    /**
     * 获取按钮图标
     */
    getButtonIcon(button) {
        // 如果有自定义图标，使用自定义图标
        if (button.icon) {
            return button.icon;
        }
        
        // 根据类型返回默认图标
        const typeIcons = {
            single: '⌨️',
            multi: '🔢',
            toggle: '🔄'
        };
        
        return typeIcons[button.type] || '⌨️';
    }
    
    /**
     * 获取按钮类型样式类
     */
    getButtonTypeClass(type) {
        return `button-type-${type}`;
    }
    
    /**
     * 绑定事件
     */
    bindEvents() {
        if (!this.shortcutBar) return;
        
        // 使用事件委托处理按钮点击
        this.shortcutBar.addEventListener('click', (e) => {
            const button = e.target.closest('.shortcut-button');
            if (!button) return;
            
            const buttonId = button.getAttribute('data-id');
            const buttonType = button.getAttribute('data-type');
            const buttonData = this.buttons.find(b => b.id === buttonId);
            
            if (!buttonData) {
                console.error('[ShortcutActions] 找不到按钮数据:', buttonId);
                return;
            }
            
            this.executeButtonAction(buttonData, button);
        });
    }
    
    /**
     * 执行按钮动作
     */
    async executeButtonAction(buttonData, buttonElement) {
        try {
            // 添加点击动画
            this.addButtonAnimation(buttonElement, buttonData.type);
            
            // 根据按钮类型执行不同动作
            if (buttonData.type === 'single') {
                await this.executeSingleAction(buttonData);
            } else if (buttonData.type === 'multi') {
                await this.executeMultiAction(buttonData);
            } else if (buttonData.type === 'toggle') {
                await this.executeToggleAction(buttonData, buttonElement);
            }
            
            console.log(`[ShortcutActions] 已执行按钮: ${buttonData.name}`);
        } catch (error) {
            console.error('[ShortcutActions] 执行按钮动作失败:', error);
            UIComponents.showToast('执行失败: ' + error.message, 'error');
        }
    }
    
    /**
     * 执行单次点击动作
     */
    async executeSingleAction(buttonData) {
        if (!buttonData.shortcut) {
            throw new Error('快捷键未配置');
        }
        
        await window.networkRequest.executeShortcut(buttonData.shortcut);
    }
    
    /**
     * 执行多次点击动作
     */
    async executeMultiAction(buttonData) {
        if (!buttonData.multiActions || buttonData.multiActions.length === 0) {
            throw new Error('多次点击动作未配置');
        }
        
        for (const action of buttonData.multiActions) {
            if (!action.shortcut) continue;
            
            const count = action.count || 1;
            for (let i = 0; i < count; i++) {
                await window.networkRequest.executeShortcut(action.shortcut);
                // 短暂延迟，避免执行过快
                await new Promise(resolve => setTimeout(resolve, 100));
            }
        }
    }
    
    /**
     * 执行激活模式动作
     */
    async executeToggleAction(buttonData, buttonElement) {
        if (!buttonData.toggleActions || buttonData.toggleActions.length === 0) {
            throw new Error('激活模式动作未配置');
        }
        
        // 检查当前是否已激活
        const isActive = buttonElement.classList.contains('active');
        
        if (isActive) {
            // 执行取消激活动作
            const cancelAction = buttonData.toggleActions.find(action => 
                action.name && action.name.toLowerCase().includes('取消')
            );
            
            if (cancelAction && cancelAction.shortcut) {
                await window.networkRequest.executeShortcut(cancelAction.shortcut);
            }
            
            // 移除激活状态
            buttonElement.classList.remove('active');
        } else {
            // 执行激活动作
            const activateAction = buttonData.toggleActions.find(action => 
                action.name && !action.name.toLowerCase().includes('取消')
            );
            
            if (activateAction && activateAction.shortcut) {
                await window.networkRequest.executeShortcut(activateAction.shortcut);
            }
            
            // 添加激活状态
            buttonElement.classList.add('active');
            
            // 如果有自动关闭时间，设置定时器
            if (buttonData.autoCloseTime && buttonData.autoCloseTime > 0) {
                setTimeout(() => {
                    if (buttonElement.classList.contains('active')) {
                        buttonElement.classList.remove('active');
                        
                        // 执行取消激活动作
                        const cancelAction = buttonData.toggleActions.find(action => 
                            action.name && action.name.toLowerCase().includes('取消')
                        );
                        
                        if (cancelAction && cancelAction.shortcut) {
                            window.networkRequest.executeShortcut(cancelAction.shortcut);
                        }
                    }
                }, buttonData.autoCloseTime * 1000);
            }
        }
    }
    
    /**
     * 添加按钮动画
     */
    addButtonAnimation(buttonElement, buttonType) {
        // 移除所有动画类
        buttonElement.classList.remove('btn-single-anim', 'btn-multi-anim', 'btn-toggle-on-anim', 'btn-toggle-off-anim');
        
        // 根据类型添加动画
        if (buttonType === 'single') {
            buttonElement.classList.add('btn-single-anim');
        } else if (buttonType === 'multi') {
            buttonElement.classList.add('btn-multi-anim');
        } else if (buttonType === 'toggle') {
            const isActive = buttonElement.classList.contains('active');
            if (isActive) {
                buttonElement.classList.add('btn-toggle-off-anim');
            } else {
                buttonElement.classList.add('btn-toggle-on-anim');
            }
        }
        
        // 动画结束后移除动画类
        setTimeout(() => {
            buttonElement.classList.remove('btn-single-anim', 'btn-multi-anim', 'btn-toggle-on-anim', 'btn-toggle-off-anim');
        }, 600);
    }
    
    /**
     * 刷新按钮
     */
    async refresh() {
        await this.loadButtons();
        this.renderButtons();
    }
    
    /**
     * 获取按钮状态
     */
    getButtonStatus(buttonId) {
        const button = this.buttons.find(b => b.id === buttonId);
        if (!button) return null;
        
        const buttonElement = document.querySelector(`[data-id="${buttonId}"]`);
        if (!buttonElement) return null;
        
        return {
            data: button,
            isActive: buttonElement.classList.contains('active')
        };
    }
    
    /**
     * 设置按钮激活状态
     */
    setButtonActive(buttonId, isActive) {
        const buttonElement = document.querySelector(`[data-id="${buttonId}"]`);
        if (!buttonElement) return;
        
        if (isActive) {
            buttonElement.classList.add('active');
        } else {
            buttonElement.classList.remove('active');
        }
    }
    
    /**
     * 添加倒计时条
     */
    addCountdownBar(buttonElement, duration) {
        // 移除现有倒计时条
        const existingBar = buttonElement.querySelector('.toggle-countdown-bar');
        if (existingBar) {
            existingBar.remove();
        }
        
        // 创建倒计时条
        const countdownBar = document.createElement('div');
        countdownBar.className = 'toggle-countdown-bar';
        countdownBar.style.animationDuration = `${duration}s`;
        
        buttonElement.appendChild(countdownBar);
        
        // 动画结束后移除
        setTimeout(() => {
            if (buttonElement.contains(countdownBar)) {
                buttonElement.removeChild(countdownBar);
            }
        }, duration * 1000);
    }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ShortcutActions;
} else {
    window.ShortcutActions = ShortcutActions;
}