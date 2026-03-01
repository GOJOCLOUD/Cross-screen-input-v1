// 主入口文件
// 加载所有模块并初始化应用

// 检查API函数是否加载
console.log('[KPSR] main.js 开始加载');
console.log('[KPSR] loadMouseButtonsFromServer:', typeof window.loadMouseButtonsFromServer);
console.log('[KPSR] saveMouseButtonToServer:', typeof window.saveMouseButtonToServer);

// 等待DOM加载完成
document.addEventListener('DOMContentLoaded', async function() {
    Logger.log('DOM加载完成，初始化应用');
    Logger.log('API函数检查 - loadMouseButtonsFromServer:', typeof window.loadMouseButtonsFromServer);
    Logger.log('API函数检查 - saveMouseButtonToServer:', typeof window.saveMouseButtonToServer);
    
    // 初始化DOM元素引用
    const DOM = {
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

    Logger.log('DOM元素:', DOM);

    if (!DOM.input || !DOM.list || !DOM.welcome) {
        Logger.error('DOM元素未找到！');
        showToast('页面加载错误，请刷新重试');
        return;
    }

    // 输入框自动调整高度
    DOM.input.addEventListener('input', () => {
        DOM.input.style.height = 'auto';
        DOM.input.style.height = DOM.input.scrollHeight + 'px';
        const hasValue = DOM.input.value.trim().length > 0;
        DOM.sendBtn.disabled = !hasValue;
        DOM.sendBtn.classList.toggle('active', hasValue);
    });

    // 渲染消息
    const renderMessage = (text) => {
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
    };

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

    // 处理发送
    async function handleSend(e) {
        if (e) e.preventDefault();
        
        Logger.log('handleSend被调用');
        const content = DOM.input.value.trim();
        Logger.log('输入内容:', content);
        
        if (!content || DOM.sendBtn.disabled) {
            Logger.log('内容为空或按钮禁用，退出');
            return;
        }

        Logger.log('清空输入框');
        DOM.input.value = '';
        DOM.input.style.height = 'auto';
        DOM.sendBtn.disabled = true;
        DOM.sendBtn.classList.remove('active');

        Logger.log('调用renderMessage');
        renderMessage(content);

        try {
            Logger.log('发送请求到服务器');
            const result = await window.networkRequest.sendClipboardData(content);
            Logger.log('发送成功:', result);

        } catch (error) {
            Logger.error('发送失败:', error);
            showToast('发送失败: ' + error.message);
        }
    }

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

    // 初始化应用
    async function initApp() {
        // 检查设备是否已配对
        const deviceId = window.networkRequest.deviceId;
        const deviceName = localStorage.getItem('kpsr_device_name') || 'KPSR Mobile Client';
        
        try {
            const response = await window.networkRequest.post('/api/network/verify-device', {
                device_id: deviceId,
                name: deviceName
            });
            
            const result = await response.json();
            
            if (!result.paired) {
                // 设备未配对，跳转到配对页面
                window.location.href = '/pair';
                return;
            }
        } catch (error) {
            console.error('检查配对状态失败:', error);
            // 如果是认证错误，跳转到配对页面
            if (error.message.includes('认证') || error.message.includes('401')) {
                window.location.href = '/pair';
                return;
            }
        }
        
        // 设备已配对，启动心跳检测
        window.networkRequest.startHeartbeat(deviceName);
        
        // 加载快捷键按钮
        await loadShortcutButtons();
        
        // 设置网络状态监听
        window.networkRequest.addStatusListener((isOnline) => {
            if (isOnline) {
                Logger.log('网络已连接');
                showToast('网络已连接', 'success');
            } else {
                Logger.log('网络已断开');
                showToast('网络已断开，请检查网络连接', 'error');
            }
        });
    }

    // 页面可见性变化处理
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            // 页面变为可见时，重新启动心跳
            window.networkRequest.startHeartbeat('KPSR Mobile Client');
        } else {
            // 页面不可见时，停止心跳以节省资源
            window.networkRequest.stopHeartbeat();
        }
    });

    // 页面卸载时停止心跳
    window.addEventListener('beforeunload', () => {
        window.networkRequest.stopHeartbeat();
    });

    // 初始化应用
    initApp().catch(error => {
        Logger.error('应用初始化失败:', error);
    });

    // 侧边栏功能
    function toggleSidebar() {
        DOM.sidebar.classList.toggle('active');
        DOM.overlay.classList.toggle('active');
        document.body.style.overflow = DOM.sidebar.classList.contains('active') ? 'hidden' : '';
    }

    function closeSidebar() {
        DOM.sidebar.classList.remove('active');
        DOM.overlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    // 侧边栏事件
    if (DOM.menuBtn) {
        DOM.menuBtn.addEventListener('click', toggleSidebar);
    }

    if (DOM.overlay) {
        DOM.overlay.addEventListener('click', closeSidebar);
    }

    // 跳转到键盘快捷键设置页面
    window.goToShortcutSettings = function() {
        closeSidebar();
        showSettings();
    };

    window.goToMouseSettings = function() {
        closeSidebar();
        showMouseSettings();
    };

    // 设置遮罩层功能
    window.showSettings = async function() {
        Logger.log('showSettings 被调用');
        const overlay = document.getElementById('settingsOverlay');
        if (overlay) {
            // 先修改标题为键盘快捷键设置（在显示面板之前）
            const headerTitle = overlay.querySelector('.settings-header h3');
            if (headerTitle) {
                headerTitle.textContent = '键盘快捷键设置';
                Logger.log('标题已修改为: 键盘快捷键设置');
            }
            
            // 显示面板
            overlay.classList.add('active');
            document.body.style.overflow = 'hidden';
            
            // 渲染内容
            await renderSettingsContent();
        } else {
            Logger.error('settingsOverlay 元素未找到');
        }
    };

    window.showMouseSettings = async function() {
        Logger.log('showMouseSettings 被调用');
        const overlay = document.getElementById('settingsOverlay');
        if (overlay) {
            // 先修改标题为鼠标按键设置（在显示面板之前）
            const headerTitle = overlay.querySelector('.settings-header h3');
            if (headerTitle) {
                headerTitle.textContent = '鼠标按键设置';
                Logger.log('标题已修改为: 鼠标按键设置');
            } else {
                Logger.error('找不到标题元素');
            }
            
            // 显示面板
            overlay.classList.add('active');
            document.body.style.overflow = 'hidden';
            
            // 渲染内容
            await renderMouseSettingsContent();
        } else {
            Logger.error('settingsOverlay 元素未找到');
        }
    };

    window.closeSettings = function() {
        const overlay = document.getElementById('settingsOverlay');
        if (overlay) {
            overlay.classList.remove('active');
            document.body.style.overflow = '';
        }
    };

    // 点击遮罩层背景关闭设置
    const settingsOverlay = document.getElementById('settingsOverlay');
    if (settingsOverlay) {
        settingsOverlay.addEventListener('click', function(e) {
            if (e.target === settingsOverlay) {
                closeSettings();
            }
        });
    }

    // 菜单项点击事件
    const menuItems = document.querySelectorAll('.menu-item');
    menuItems.forEach(item => {
        item.addEventListener('click', function() {
            const text = this.querySelector('span').textContent;
            Logger.log('Menu item clicked:', text);
            
            // Close sidebar after menu item click
            closeSidebar();
        });
    });

    // 初始化快捷键功能
    (async function() {
        Logger.log('快捷键功能初始化');

        // 渲染快捷键按钮
        window.renderShortcutButtons = async function() {
            const shortcutBar = document.getElementById('shortcutBar');
            if (!shortcutBar) return;
            
            // 清空容器
            shortcutBar.innerHTML = '';
            
            // 从服务器加载按钮
            const buttons = await loadButtonsFromServer();
            
            if (buttons.length === 0) {
                return;
            }
            
            // 按顺序排序
            buttons.sort((a, b) => (a.order || 0) - (b.order || 0));
            
            // 获取激活状态（只用于toggle类型）
            const activeButtons = getActiveButtons();
            
            // 渲染每个按钮
            buttons.forEach(button => {
                const buttonElement = document.createElement('button');
                buttonElement.className = 'shortcut-button';
                buttonElement.id = `shortcut-${button.id}`;
                
                // 添加按钮类型类，用于区分动画
                buttonElement.classList.add(`button-type-${button.type}`);
                
                buttonElement.innerHTML = `
                    <div class="shortcut-button-icon">${sanitizeInput(button.icon) || '🔘'}</div>
                    <div class="shortcut-button-name">${sanitizeInput(button.name)}</div>
                `;
                
                // 只对toggle类型按钮应用激活状态
                if (button.type === 'toggle' && activeButtons[button.id]) {
                    buttonElement.classList.add('active');
                } else {
                    // 确保single和multi类型按钮不显示激活状态
                    buttonElement.classList.remove('active');
                }
                
                // 添加点击事件
                // 注意：确保button对象完整传递，包括autoCloseDuration
                buttonElement.addEventListener('click', () => {
                    Logger.log(`按钮 ${button.id} 被点击，完整按钮数据:`, button);
                    Logger.log(`按钮 ${button.id} 的 autoCloseDuration:`, button.autoCloseDuration);
                    handleShortcutClick(button);
                });
                
                shortcutBar.appendChild(buttonElement);
            });
        };

        // 鼠标按键映射在后台运行，不在主页显示按钮
        // 处理鼠标按钮点击（用于设置页面测试）
        function handleMouseClick(button) {
            Logger.log('鼠标按钮点击:', button);
            Logger.log('执行快捷键:', button.action);
            
            // 验证按钮数据
            if (!button.action) {
                Logger.error('鼠标按钮缺少操作:', button);
                showToast('按钮配置错误：缺少快捷键');
                return;
            }
            
            // 添加点击动画
            const buttonElement = document.getElementById(`mouse-${button.id}`);
            if (buttonElement) {
                buttonElement.classList.add('mouse-button-clicked');
                setTimeout(() => {
                    buttonElement.classList.remove('mouse-button-clicked');
                }, 300);
            }
            
            // 执行键盘快捷键（和键盘快捷键功能一样）
            executeShortcutOnServer(button.action, 'single')
                .then(result => {
                    Logger.log('快捷键执行成功:', result);
                    // 成功时不显示提示，只在失败时提示
                })
                .catch(error => {
                    Logger.error('快捷键执行失败:', error);
                    showToast('操作执行失败: ' + error.message);
                });
        }

        // 验证按钮数据完整性
        function validateButtonData(button) {
            if (!button || !button.type) {
                return { valid: false, message: '按钮数据不完整：缺少类型' };
            }
            
            switch (button.type) {
                case 'single':
                    if (!button.shortcut) {
                        return { valid: false, message: '单次点击按钮缺少快捷键' };
                    }
                    // 检查是否有其他类型的字段（数据污染）
                    if (button.multiActions || button.toggleActions) {
                        Logger.warn('单次点击按钮包含其他类型字段，建议清理:', button);
                    }
                    break;
                
                case 'multi':
                    if (!button.multiActions || button.multiActions.length === 0) {
                        return { valid: false, message: '多次点击按钮缺少动作配置' };
                    }
                    // 检查是否有其他类型的字段
                    if (button.shortcut || button.toggleActions) {
                        Logger.warn('多次点击按钮包含其他类型字段，建议清理:', button);
                    }
                    break;
                
                case 'toggle':
                    if (!button.toggleActions || !button.toggleActions.activate || !button.toggleActions.deactivate) {
                        return { valid: false, message: '激活模式按钮配置不完整' };
                    }
                    // 检查是否有其他类型的字段
                    if (button.shortcut || button.multiActions) {
                        Logger.warn('激活模式按钮包含其他类型字段，建议清理:', button);
                    }
                    break;
                
                default:
                    return { valid: false, message: `未知的按钮类型: ${button.type}` };
            }
            
            return { valid: true };
        }

        // 处理按钮点击
        function handleShortcutClick(button) {
            // 验证按钮数据
            const validation = validateButtonData(button);
            if (!validation.valid) {
                Logger.error('按钮数据验证失败:', validation.message, button);
                showToast('按钮配置错误：' + validation.message);
                return;
            }
            
            // 验证按钮类型和字段的匹配
            if (!button.type) {
                Logger.error('按钮类型未定义:', button);
                showToast('按钮配置错误：类型未定义');
                return;
            }
            
            switch (button.type) {
                case 'single':
                    // 验证单次点击类型
                    if (!button.shortcut) {
                        Logger.error('单次点击按钮缺少快捷键:', button);
                        showToast('按钮配置错误：缺少快捷键');
                        return;
                    }
                    // 执行快捷键，但不更新UI状态（single类型不保持激活状态）
                    const singleButton = document.getElementById(`shortcut-${button.id}`);
                    if (singleButton) {
                        // 先确保移除所有可能的状态类
                        singleButton.classList.remove('active', 'btn-toggle-pulse');
                        
                        // 添加点击动画
                        singleButton.classList.remove('btn-single-anim');
                        void singleButton.offsetWidth; // 触发重排
                        singleButton.classList.add('btn-single-anim');
                        
                        // 动画结束后，完全重置按钮状态
                        setTimeout(() => {
                            singleButton.classList.remove('btn-single-anim', 'active', 'btn-toggle-pulse');
                            // 确保移除所有可能的状态样式
                            singleButton.style.transform = '';
                            singleButton.style.boxShadow = '';
                            singleButton.style.background = '';
                            singleButton.style.color = '';
                        }, 600);
                    }
                    sendShortcutToServer(button.shortcut, 'single');
                    break;
                
                case 'multi':
                    // 验证多次点击类型
                    if (!button.multiActions || button.multiActions.length === 0) {
                        Logger.error('多次点击按钮缺少动作配置:', button);
                        showToast('按钮配置错误：缺少动作配置');
                        return;
                    }
                    // 添加点击动画（和Single一样，但更快）
                    const multiButton = document.getElementById(`shortcut-${button.id}`);
                    if (multiButton) {
                        // 确保移除所有可能的状态类
                        multiButton.classList.remove('active', 'btn-toggle-pulse', 'btn-multi-anim');
                        void multiButton.offsetWidth; // 触发重排
                        multiButton.classList.add('btn-multi-anim');
                        
                        setTimeout(() => {
                            multiButton.classList.remove('btn-multi-anim', 'active', 'btn-toggle-pulse');
                            multiButton.style.transform = '';
                            multiButton.style.boxShadow = '';
                            multiButton.style.background = '';
                            multiButton.style.color = '';
                        }, 300);
                    }
                    handleMultiClick(button);
                    break;
                
                case 'toggle':
                    // 验证激活模式类型
                    if (!button.toggleActions || !button.toggleActions.activate || !button.toggleActions.deactivate) {
                        Logger.error('激活模式按钮缺少动作配置:', button);
                        showToast('按钮配置错误：缺少激活/取消激活配置');
                        return;
                    }
                    handleToggleClick(button);
                    break;
                
                default:
                    Logger.error('未知的按钮类型:', button.type);
                    showToast('按钮配置错误：未知类型');
                    return;
            }
        }

        // 处理多次点击
        function handleMultiClick(button) {
            // 安全检查
            if (!button.multiActions || button.multiActions.length === 0) {
                Logger.error('多次点击按钮缺少 multiActions:', button);
                showToast('按钮配置错误：缺少动作配置');
                return;
            }
            
            const clickCount = getClickCount(button.id);
            const actions = button.multiActions;
            
            // 获取当前点击对应的动作
            const actionIndex = clickCount % actions.length;
            const action = actions[actionIndex];
            
            if (!action || !action.shortcut) {
                Logger.error('多次点击动作配置错误:', action);
                showToast('按钮配置错误：动作配置错误');
                return;
            }
            
            sendShortcutToServer(action.shortcut, 'multi');
            incrementClickCount(button.id);
        }

        // 处理激活/取消激活点击
        function handleToggleClick(button) {
            // 安全检查
            if (!button.toggleActions) {
                Logger.error('激活模式按钮缺少 toggleActions:', button);
                showToast('按钮配置错误：缺少激活配置');
                return;
            }
            
            if (!button.toggleActions.activate || !button.toggleActions.deactivate) {
                Logger.error('激活模式按钮配置不完整:', button);
                showToast('按钮配置错误：激活配置不完整');
                return;
            }
            
            // 只对toggle类型按钮切换状态
            if (button.type !== 'toggle') {
                Logger.error('非toggle类型按钮调用了handleToggleClick:', button);
                return;
            }
            
            const toggleButton = document.getElementById(`shortcut-${button.id}`);
            const wasActive = toggleButton && toggleButton.classList.contains('active');
            const isActive = toggleButtonState(button.id);
            const shortcut = isActive ? button.toggleActions.activate : button.toggleActions.deactivate;
            
            sendShortcutToServer(shortcut, 'toggle');
            updateButtonUI(button.id, isActive);
            
            // 添加激活/取消激活动画
            if (toggleButton) {
                toggleButton.classList.remove('btn-toggle-on-anim', 'btn-toggle-off-anim', 'btn-toggle-pulse');
                
                if (isActive && !wasActive) {
                    // 激活动画
                    void toggleButton.offsetWidth; // 触发重排
                    toggleButton.classList.add('btn-toggle-on-anim');
                    setTimeout(() => {
                        toggleButton.classList.remove('btn-toggle-on-anim');
                        toggleButton.classList.add('btn-toggle-pulse');
                        // 如果设置了自动关闭，添加倒计时
                        // 注意：倒计时条应该在激活动画结束后立即显示，与定时器同步
                        if (button.autoCloseDuration && button.autoCloseDuration > 0) {
                            addCountdownBar(toggleButton, button.autoCloseDuration);
                        }
                    }, 400); // 与btnToggleOn动画时长一致（0.4s）
                } else if (!isActive && wasActive) {
                    // 取消激活动画
                    removeCountdownBar(toggleButton);
                    toggleButton.classList.remove('btn-toggle-pulse');
                    void toggleButton.offsetWidth; // 触发重排
                    toggleButton.classList.add('btn-toggle-off-anim');
                    setTimeout(() => {
                        toggleButton.classList.remove('btn-toggle-off-anim');
                    }, 400);
                }
            }
            
            // 处理自动关闭
            if (isActive) {
                // 激活状态：启动自动关闭定时器
                const autoCloseDuration = button.autoCloseDuration;
                
                // 检查autoCloseDuration是否存在且大于0
                // 注意：autoCloseDuration可能是数字、字符串或null/undefined
                const duration = parseInt(autoCloseDuration, 10);
                
                if (!isNaN(duration) && duration > 0) {
                    startAutoCloseTimer(button.id, duration, button);
                }
                
                // 启动剪贴板监听（用于检测操作完成）
                startClipboardMonitor(button.id, button);
            } else {
                // 取消激活状态：清除自动关闭定时器和剪贴板监听
                clearAutoCloseTimer(button.id);
                stopClipboardMonitor(button.id);
            }
        }

        // 发送快捷键到服务器
        async function sendShortcutToServer(shortcut, actionType = 'single') {
            try {
                const result = await executeShortcutOnServer(shortcut, actionType);
                Logger.log('快捷键执行成功:', result);
                // 成功时不显示提示，只在失败时提示
            } catch (error) {
                Logger.error('快捷键执行失败:', error);
                showToast('快捷键执行失败，请重试');
            }
        }

        // 切换按钮激活状态
        function toggleButtonState(buttonId) {
            let activeButtons = getActiveButtons();
            activeButtons[buttonId] = !activeButtons[buttonId];
            saveActiveButtons(activeButtons);
            return activeButtons[buttonId];
        }

        // 获取按钮激活状态
        function getActiveButtons() {
            try {
                const activeButtons = localStorage.getItem('active_buttons');
                return activeButtons ? JSON.parse(activeButtons) : {};
            } catch (error) {
                Logger.error('加载激活状态失败:', error);
                return {};
            }
        }

        // 保存按钮激活状态
        function saveActiveButtons(activeButtons) {
            try {
                localStorage.setItem('active_buttons', JSON.stringify(activeButtons));
            } catch (error) {
                Logger.error('保存激活状态失败:', error);
            }
        }

        // 获取按钮点击次数
        function getClickCount(buttonId) {
            try {
                const clickCounts = localStorage.getItem('click_counts');
                const counts = clickCounts ? JSON.parse(clickCounts) : {};
                return counts[buttonId] || 0;
            } catch (error) {
                Logger.error('加载点击次数失败:', error);
                return 0;
            }
        }

        // 增加按钮点击次数
        function incrementClickCount(buttonId) {
            try {
                const clickCounts = localStorage.getItem('click_counts');
                const counts = clickCounts ? JSON.parse(clickCounts) : {};
                counts[buttonId] = (counts[buttonId] || 0) + 1;
                localStorage.setItem('click_counts', JSON.stringify(counts));
            } catch (error) {
                Logger.error('保存点击次数失败:', error);
            }
        }

        // 更新按钮UI
        function updateButtonUI(buttonId, isActive) {
            const buttonElement = document.getElementById(`shortcut-${buttonId}`);
            if (buttonElement) {
                if (isActive) {
                    buttonElement.classList.add('active');
                } else {
                    buttonElement.classList.remove('active');
                }
            }
        }

        // 暴露函数到全局作用域，供定时器回调使用
        window._kpsr = {
            getActiveButtons: getActiveButtons,
            saveActiveButtons: saveActiveButtons,
            sendShortcutToServer: sendShortcutToServer,
            updateButtonUI: updateButtonUI
        };

        // 初始化
        await renderShortcutButtons();
        Logger.log('快捷键功能初始化完成');

    })();

    // 渲染设置界面内容
    window.renderSettingsContent = async function() {
        Logger.log('renderSettingsContent 被调用');
        const content = document.getElementById('settingsContent');
        if (!content) {
            Logger.error('settingsContent 元素未找到');
            return;
        }
        
        // 显示加载状态
        content.innerHTML = `
            <div class="loading-state" style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 20px;">
                <div class="spinner" style="width: 40px; height: 40px; border: 4px solid #f3f3f3; border-top: 4px solid #007AFF; border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 16px;"></div>
                <p style="color: #8e8e8e; font-size: 16px;">加载中...</p>
            </div>
            <style>
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
        `;
        
        try {
            // 获取平台信息
            const platformInfo = await getPlatformInfo();
            
            // 从服务器加载按钮
            const buttons = await loadButtonsFromServer();
            Logger.log('加载的按钮:', buttons);
            
            // 渲染按钮列表
            let html = `
                <!-- 平台提示 -->
                ${platformInfo.platform === 'windows' ? `
                    <div class="platform-notice" style="background: #d1ecf1; border: 1px solid #0c5460; padding: 12px; margin-bottom: 20px; border-radius: 4px;">
                        <strong>💡 平台提示：</strong>检测到您使用的是 Windows 系统。在 Windows 上，<code>ctrl</code> 映射到 Control 键。
                    </div>
                ` : ''}
                
                <div class="button-list-section">
                    <h2>已配置的按钮</h2>
                    <div id="buttonList">
                        ${buttons.length === 0 ? renderEmptyState() : renderButtonList(buttons)}
                    </div>
                </div>
                
                <div class="add-button-container">
                    <button class="add-button" onclick="showAddForm()">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="12" y1="5" x2="12" y2="19"></line>
                            <line x1="5" y1="12" x2="19" y2="12"></line>
                        </svg>
                        添加按钮
                    </button>
                </div>
                
                <div class="form-container" id="configForm" style="display: none;">
                    ${renderConfigForm()}
                </div>
            `;
            
            content.innerHTML = html;
            Logger.log('设置内容已渲染');
        } catch (error) {
            Logger.error('渲染设置内容时出错:', error);
            content.innerHTML = '<div class="empty-state"><h3>加载失败</h3><p>请刷新页面重试</p></div>';
        }
    };

    // 渲染鼠标设置界面内容
    window.renderMouseSettingsContent = async function() {
        Logger.log('renderMouseSettingsContent 被调用');
        const content = document.getElementById('settingsContent');
        if (!content) {
            Logger.error('settingsContent 元素未找到');
            return;
        }
        
        // 显示加载状态
        content.innerHTML = `
            <div class="loading-state" style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 20px;">
                <div class="spinner" style="width: 40px; height: 40px; border: 4px solid #f3f3f3; border-top: 4px solid #007AFF; border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 16px;"></div>
                <p style="color: #8e8e8e; font-size: 16px;">加载中...</p>
            </div>
            <style>
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
        `;
        
        try {
            // 获取平台信息（使用鼠标专用 API，如果失败则使用默认值）
            let platformInfo = { platform: 'unknown' };
            try {
                Logger.log('正在获取鼠标平台信息...');
                const response = await fetch('/api/mouse/platform');
                Logger.log('平台信息响应状态:', response.status);
                if (response.ok) {
                    platformInfo = await response.json();
                    Logger.log('平台信息:', platformInfo);
                }
            } catch (e) {
                Logger.warn('获取鼠标平台信息失败，使用默认值:', e);
            }
            
            // 从服务器加载鼠标按钮
            Logger.log('正在加载鼠标按钮...');
            let buttons = [];
            try {
                buttons = await loadMouseButtonsFromServer();
                Logger.log('加载的鼠标按钮:', buttons);
            } catch (e) {
                Logger.error('加载鼠标按钮失败:', e);
                buttons = [];
            }
            
            // 确保 buttons 是数组
            if (!Array.isArray(buttons)) {
                Logger.warn('buttons 不是数组，重置为空数组');
                buttons = [];
            }
            
            Logger.log('开始渲染 HTML，buttons 数量:', buttons.length);
            
            // 渲染按钮列表
            Logger.log('调用 renderMouseEmptyState 或 renderMouseButtonList...');
            const buttonListHtml = buttons.length === 0 ? renderMouseEmptyState() : renderMouseButtonList(buttons);
            Logger.log('按钮列表 HTML 生成完成');
            
            Logger.log('调用 renderMouseConfigForm...');
            const configFormHtml = renderMouseConfigForm();
            Logger.log('配置表单 HTML 生成完成');
            
            let html = `
                <!-- 平台提示 -->
                ${platformInfo.platform === 'windows' ? `
                    <div class="platform-notice" style="background: #d1ecf1; border: 1px solid #0c5460; padding: 12px; margin-bottom: 20px; border-radius: 4px;">
                        <strong>💡 平台提示：</strong>检测到您使用的是 Windows 系统。在 Windows 上，<code>ctrl</code> 映射到 Control 键。
                    </div>
                ` : ''}
                
                <div class="button-list-section">
                    <h2>已配置的鼠标按键映射</h2>
                    <div id="mouseButtonList">
                        ${buttonListHtml}
                    </div>
                </div>
                
                <div class="add-button-container">
                    <button class="add-button" onclick="showMouseAddForm()">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="12" y1="5" x2="12" y2="19"></line>
                            <line x1="5" y1="12" x2="19" y2="12"></line>
                        </svg>
                        添加鼠标按钮
                    </button>
                </div>
                
                <div class="form-container" id="mouseConfigForm" style="display: none;">
                    ${configFormHtml}
                </div>
            `;
            
            content.innerHTML = html;
            Logger.log('鼠标设置内容已渲染');
        } catch (error) {
            Logger.error('渲染鼠标设置内容时出错:', error);
            Logger.error('错误堆栈:', error.stack);
            content.innerHTML = `<div class="empty-state"><h3>加载失败</h3><p>错误: ${error.message}</p><p style="font-size:12px;color:#888;">请检查控制台获取详细信息</p></div>`;
        }
    };

    // 渲染配置表单
    function renderConfigForm() {
        return `
            <h2>配置按钮</h2>
            
            <div class="form-group">
                <label for="buttonName">按钮名称</label>
                <input type="text" id="buttonName" placeholder="例如：粘贴">
            </div>

            <div class="form-group">
                <label for="buttonIcon">按钮图标</label>
                <input type="text" id="buttonIcon" placeholder="例如：📋 或图标URL">
            </div>

            <div class="form-group">
                <label for="actionType">操作类型</label>
                <select id="actionType" onchange="toggleConfigSections()">
                    <option value="single">单次点击</option>
                    <option value="multi">多次点击循环</option>
                    <option value="toggle">激活/取消激活</option>
                </select>
            </div>

            <!-- 单次点击配置 -->
            <div class="form-group" id="singleConfig">
                <label for="singleShortcut">快捷键组合</label>
                <input type="text" id="singleShortcut" placeholder="例如：Ctrl+V">
            </div>

            <!-- 多次点击配置 -->
            <div class="config-section" id="multiConfig" style="display: none;">
                <h3>多次点击配置</h3>
                <div id="multiActions">
                    <div class="multi-action-item">
                        <label>点击 1</label>
                        <input type="text" placeholder="例如：Ctrl+C">
                    </div>
                    <div class="multi-action-item">
                        <label>点击 2</label>
                        <input type="text" placeholder="例如：Ctrl+V">
                    </div>
                </div>
                <button class="add-action-button" onclick="addMultiAction()">添加点击动作</button>
            </div>

            <!-- 激活模式配置 -->
            <div class="config-section" id="toggleConfig" style="display: none;">
                <h3>激活模式配置</h3>
                <div class="toggle-action-item">
                    <label>激活时快捷键</label>
                    <input type="text" id="activateShortcut" placeholder="例如：Ctrl+Shift+S">
                </div>
                <div class="toggle-action-item">
                    <label>取消激活时快捷键</label>
                    <input type="text" id="deactivateShortcut" placeholder="例如：Esc">
                </div>
                <div class="toggle-action-item">
                    <label>自动关闭时长（秒）</label>
                    <input type="number" id="autoCloseDuration" min="0" step="1" placeholder="0表示不自动关闭，留空也表示不自动关闭">
                    <div style="font-size: 12px; color: #8e8e8e; margin-top: 4px;">设置后，按钮激活后会在指定秒数后自动取消激活。设置为0或留空表示不自动关闭。</div>
                </div>
            </div>

            <!-- 表单按钮 -->
            <div class="form-buttons">
                <button class="cancel-button" onclick="hideForm()">取消</button>
                <button class="save-button" onclick="saveButton()">保存</button>
            </div>
        `;
    }

    // 渲染按钮列表
    function renderButtonList(buttons) {
        if (buttons.length === 0) {
            return renderEmptyState();
        }
        
        return buttons.map(button => {
            let typeText = '';
            switch (button.type) {
                case 'single':
                    typeText = '单次点击';
                    break;
                case 'multi':
                    typeText = '多次点击循环';
                    break;
                case 'toggle':
                    typeText = '激活/取消激活';
                    break;
            }
            
            return `
                <div class="button-item">
                    <div class="button-info">
                        <div class="button-icon">${sanitizeInput(button.icon) || '🔘'}</div>
                        <div class="button-details">
                            <div class="button-name">${sanitizeInput(button.name)}</div>
                            <div class="button-type">${typeText}</div>
                        </div>
                    </div>
                    <div class="button-actions">
                        <button class="action-button" onclick="editButton('${button.id}')">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                            </svg>
                        </button>
                        <button class="action-button delete-button" onclick="deleteButton('${button.id}')">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <polyline points="3 6 5 6 21 6"></polyline>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                <line x1="10" y1="11" x2="10" y2="17"></line>
                                <line x1="14" y1="11" x2="14" y2="17"></line>
                            </svg>
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    // 渲染空状态
    function renderEmptyState() {
        return `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
                <h3>暂无配置的按钮</h3>
                <p>点击下方的 "添加按钮" 开始配置</p>
            </div>
        `;
    }

    // 渲染鼠标按钮空状态
    function renderMouseEmptyState() {
        return `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M5.5 15.5l1.5 1.5 2.5-2.5"></path>
                    <path d="M11.5 12.5l1.5 1.5 2.5-2.5"></path>
                    <path d="M17.5 9.5l1.5 1.5 2.5-2.5"></path>
                    <path d="M2 12h4l2-2 4 4 4-4 2 2h4"></path>
                </svg>
                <h3>暂无配置的鼠标按钮</h3>
                <p>点击下方的 "添加鼠标按钮" 开始配置</p>
            </div>
        `;
    }

    // 渲染鼠标按钮列表
    function renderMouseButtonList(buttons) {
        return buttons.map(button => {
            // 判断是序列还是单键
            const isSequence = button.sequence && Array.isArray(button.sequence) && button.sequence.length > 0;
            const typeLabel = isSequence ? '序列' : '单键';
            const typeBadge = isSequence 
                ? '<span style="background: #007AFF; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; margin-left: 8px;">序列</span>'
                : '';
            
            return `
                <div class="button-item" data-id="${button.id}">
                    <div class="button-info">
                        <div class="button-details">
                            <div class="button-name">${sanitizeInput(button.name)}${typeBadge}</div>
                            <div class="button-type" style="font-family: monospace; color: #666;">→ ${sanitizeInput(button.action)}</div>
                        </div>
                    </div>
                    <div class="button-actions">
                        <button class="action-button" onclick="editMouseButton('${button.id}')">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                            </svg>
                        </button>
                        <button class="action-button delete-button" onclick="deleteMouseButton('${button.id}')">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <polyline points="3 6 5 6 21 6"></polyline>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                <line x1="10" y1="11" x2="10" y2="17"></line>
                                <line x1="14" y1="11" x2="14" y2="17"></line>
                            </svg>
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    // 鼠标按键配置
    const MOUSE_KEY_CONFIG = {
        'left': '左键',
        'right': '右键',
        'middle': '中键',
        'side1': '侧键1',
        'side2': '侧键2'
    };
    
    // 渲染鼠标配置表单
    function renderMouseConfigForm() {
        return `
            <h2>配置鼠标按钮</h2>
            
            <div class="form-group">
                <label for="mouseConfigMode">配置模式</label>
                <select id="mouseConfigMode" onchange="toggleMouseConfigMode()">
                    <option value="single">单键模式</option>
                    <option value="sequence">序列模式</option>
                </select>
                <div style="font-size: 12px; color: #8e8e8e; margin-top: 4px;">
                    单键模式：单个按键触发功能<br>
                    序列模式：按键序列触发功能（如：先按侧键1，再按侧键2）
                </div>
            </div>
            
            <!-- 单键模式配置 -->
            <div id="singleKeyConfig">
                <div class="form-group">
                    <label for="mouseKeyType">鼠标按键</label>
                    <select id="mouseKeyType">
                        <option value="left">左键</option>
                        <option value="right">右键</option>
                        <option value="middle">中键</option>
                        <option value="side1">侧键1</option>
                        <option value="side2">侧键2</option>
                    </select>
                </div>
            </div>
            
            <!-- 序列模式配置 -->
            <div id="sequenceKeyConfig" style="display: none;">
                <div class="form-group">
                    <label>按键序列（按执行顺序添加）</label>
                    <div id="sequenceKeys" style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">
                        <!-- 序列按键会在这里动态添加 -->
                    </div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <select id="addSequenceKey" style="flex: 1;">
                            <option value="left">左键</option>
                            <option value="right">右键</option>
                            <option value="middle">中键</option>
                            <option value="side1">侧键1</option>
                            <option value="side2">侧键2</option>
                        </select>
                        <button type="button" onclick="addSequenceKey()" style="padding: 8px 16px; background: #007AFF; color: white; border: none; border-radius: 4px; cursor: pointer;">添加</button>
                    </div>
                    <div style="font-size: 12px; color: #8e8e8e; margin-top: 4px;">
                        提示：序列按键需要在 0.5 秒内连续按下才能触发<br>
                        例如：添加 侧键1 → 侧键2，表示先按侧键1再按侧键2触发
                    </div>
                </div>
            </div>

            <div class="form-group">
                <label for="mouseShortcut">映射的快捷键或系统命令</label>
                <input type="text" id="mouseShortcut" placeholder="例如：ctrl+v 或 launchpad">
                <div style="font-size: 12px; color: #8e8e8e; margin-top: 4px;">
                    <b>键盘快捷键：</b>ctrl+v（粘贴）、ctrl+c（复制）、ctrl+z（撤销）<br>
                    <b>Windows 系统功能：</b><br>
                    • <code>win+d</code> - 显示桌面<br>
                    • <code>win+e</code> - 打开资源管理器<br>
                    • <code>win+l</code> - 锁定屏幕<br>
                    • <code>alt+tab</code> - 切换窗口<br>
                    • <code>ctrl+alt+delete</code> - 任务管理器
                </div>
            </div>

            <!-- 表单按钮 -->
            <div class="form-buttons">
                <button class="cancel-button" onclick="hideMouseForm()">取消</button>
                <button class="save-button" onclick="saveMouseButton()">保存</button>
            </div>
        `;
    }
    
    // 当前序列按键列表
    let currentSequenceKeys = [];
    
    // 切换鼠标配置模式
    window.toggleMouseConfigMode = function() {
        const mode = document.getElementById('mouseConfigMode').value;
        const singleConfig = document.getElementById('singleKeyConfig');
        const sequenceConfig = document.getElementById('sequenceKeyConfig');
        
        if (mode === 'single') {
            singleConfig.style.display = 'block';
            sequenceConfig.style.display = 'none';
        } else {
            singleConfig.style.display = 'none';
            sequenceConfig.style.display = 'block';
        }
    };
    
    // 添加序列按键
    window.addSequenceKey = function() {
        const select = document.getElementById('addSequenceKey');
        const key = select.value;
        const keyName = MOUSE_KEY_CONFIG[key];
        
        currentSequenceKeys.push(key);
        renderSequenceKeys();
    };
    
    // 删除序列按键
    window.removeSequenceKey = function(index) {
        currentSequenceKeys.splice(index, 1);
        renderSequenceKeys();
    };
    
    // 渲染序列按键显示
    function renderSequenceKeys() {
        const container = document.getElementById('sequenceKeys');
        if (!container) return;
        
        if (currentSequenceKeys.length === 0) {
            container.innerHTML = '<div style="color: #8e8e8e; font-size: 14px;">尚未添加按键</div>';
            return;
        }
        
        container.innerHTML = currentSequenceKeys.map((key, index) => {
            const keyName = MOUSE_KEY_CONFIG[key];
            return `
                <div style="display: flex; align-items: center; background: #f0f0f0; padding: 4px 8px; border-radius: 4px; gap: 4px;">
                    ${index > 0 ? '<span style="color: #666; margin-right: 4px;">→</span>' : ''}
                    <span>${keyName}</span>
                    <button type="button" onclick="removeSequenceKey(${index})" style="background: none; border: none; cursor: pointer; color: #ff3b30; font-size: 16px; padding: 0 4px;">×</button>
                </div>
            `;
        }).join('');
    }

    // 全局变量：当前编辑的按钮ID
let editingButtonId = null;

// 全局变量：当前编辑的鼠标按钮ID
let editingMouseButtonId = null;

// 自动关闭定时器管理
const autoCloseTimers = {};  // 存储每个按钮的定时器ID

// 剪贴板监听管理
const clipboardEventSources = {};  // 存储每个按钮的 EventSource
const clipboardButtonRefs = {};    // 存储每个按钮的引用（用于回调）

// 启动剪贴板监听
async function startClipboardMonitor(buttonId, button) {
    // 保存 button 引用
    clipboardButtonRefs[buttonId] = button;
    console.log(`[剪贴板监听] 启动监听: ${buttonId}`);
    
    try {
        // 先通知后端开始监听
        const response = await fetch('/api/monitor/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ button_id: buttonId, action: 'start' })
        });
        
        if (!response.ok) {
            console.error(`[剪贴板监听] 启动失败: ${response.status}`);
            return;
        }
        
        console.log(`[剪贴板监听] 后端监听已启动`);
        
        // 建立 SSE 连接
        if (clipboardEventSources[buttonId]) {
            clipboardEventSources[buttonId].close();
        }
        
        const eventSource = new EventSource(`/api/monitor/events/${buttonId}`);
        clipboardEventSources[buttonId] = eventSource;
        
        eventSource.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                console.log(`[剪贴板监听] 收到事件:`, data);
                
                if (data.type === 'clipboard_change') {
                    console.log(`✅ [剪贴板监听] 检测到剪贴板变化，自动关闭按钮: ${buttonId}`);
                    
                    // 使用保存的 button 引用
                    const savedButton = clipboardButtonRefs[buttonId];
                    autoCloseButton(buttonId, savedButton);
                }
            } catch (e) {
                console.error(`[剪贴板监听] 解析事件失败:`, e);
            }
        };
        
        eventSource.onerror = function(error) {
            console.error(`[剪贴板监听] SSE 连接错误:`, error);
            // 连接出错时不自动重连，等待下次按钮点击
        };
        
        console.log(`[剪贴板监听] SSE 连接已建立`);
        
    } catch (error) {
        console.error(`[剪贴板监听] 启动出错:`, error);
    }
}

// 停止剪贴板监听
async function stopClipboardMonitor(buttonId) {
    console.log(`[剪贴板监听] 停止监听: ${buttonId}`);
    
    // 关闭 SSE 连接
    if (clipboardEventSources[buttonId]) {
        clipboardEventSources[buttonId].close();
        delete clipboardEventSources[buttonId];
        console.log(`[剪贴板监听] SSE 连接已关闭`);
    }
    
    // 清理 button 引用
    if (clipboardButtonRefs[buttonId]) {
        delete clipboardButtonRefs[buttonId];
    }
    
    // 通知后端停止监听
    try {
        await fetch('/api/monitor/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ button_id: buttonId, action: 'stop' })
        });
        console.log(`[剪贴板监听] 后端监听已停止`);
    } catch (error) {
        console.error(`[剪贴板监听] 停止出错:`, error);
    }
}

// 自动关闭按钮（由剪贴板变化触发）
function autoCloseButton(buttonId, button) {
    console.log(`[自动关闭] 剪贴板变化触发自动关闭: ${buttonId}`);
    
    const kpsr = window._kpsr;
    if (!kpsr) {
        console.error(`[自动关闭] 全局函数未初始化`);
        return;
    }
    
    // 检查按钮是否仍然激活
    const activeButtons = kpsr.getActiveButtons();
    if (!activeButtons[buttonId]) {
        console.log(`[自动关闭] 按钮已经处于非激活状态，跳过`);
        return;
    }
    
    // 更新状态
    activeButtons[buttonId] = false;
    kpsr.saveActiveButtons(activeButtons);
    
    // 执行取消激活快捷键
    if (button && button.toggleActions && button.toggleActions.deactivate) {
        console.log(`[自动关闭] 执行取消激活快捷键: ${button.toggleActions.deactivate}`);
        kpsr.sendShortcutToServer(button.toggleActions.deactivate, 'toggle');
    }
    
    // 更新 UI
    const toggleButton = document.getElementById(`shortcut-${buttonId}`);
    if (toggleButton) {
        removeCountdownBar(toggleButton);
        toggleButton.classList.remove('btn-toggle-pulse', 'btn-toggle-on-anim', 'active');
        void toggleButton.offsetWidth;
        toggleButton.classList.add('btn-toggle-off-anim');
        
        setTimeout(() => {
            toggleButton.classList.remove('btn-toggle-off-anim', 'active');
            toggleButton.style.transform = '';
            toggleButton.style.boxShadow = '';
            toggleButton.style.background = '';
            toggleButton.style.color = '';
        }, 300);
    }
    
    // 清除定时器和剪贴板监听
    clearAutoCloseTimer(buttonId);
    stopClipboardMonitor(buttonId);
    
    console.log(`✅ [自动关闭] 按钮 ${buttonId} 已通过剪贴板变化自动关闭`);
}

// 清除自动关闭定时器
function clearAutoCloseTimer(buttonId) {
    if (autoCloseTimers[buttonId]) {
        console.log(`[清除定时器] 清除按钮 ${buttonId} 的定时器，ID: ${autoCloseTimers[buttonId]}`);
        clearTimeout(autoCloseTimers[buttonId]);
        delete autoCloseTimers[buttonId];
    } else {
        console.log(`[清除定时器] 按钮 ${buttonId} 没有活动的定时器`);
    }
}

    // 启动自动关闭定时器
function startAutoCloseTimer(buttonId, duration, button) {
    // 使用console.log确保日志始终输出
    console.log(`🔵 [自动关闭] startAutoCloseTimer 被调用 - buttonId: ${buttonId}, duration: ${duration}`, button);
    
    // 先清除旧的定时器
    clearAutoCloseTimer(buttonId);
    
    // 如果时长为0或null，不启动定时器
    if (!duration || duration <= 0) {
        console.error(`❌ [自动关闭] 定时器启动失败：duration无效 (${duration})`);
        return;
    }
    
    // 保存取消激活快捷键，避免button对象在定时器回调中丢失
    const deactivateShortcut = button && button.toggleActions && button.toggleActions.deactivate 
        ? button.toggleActions.deactivate 
        : null;
    
    if (!deactivateShortcut) {
        console.error(`❌ [自动关闭] 无法启动定时器：按钮 ${buttonId} 缺少取消激活快捷键`, button);
        return;
    }
    
    console.log(`⏰ [自动关闭] 启动定时器，将在 ${duration} 秒后执行自动关闭，取消激活快捷键: ${deactivateShortcut}`);
    console.log(`⏰ [自动关闭] 定时器ID将存储在: autoCloseTimers[${buttonId}]`);
    
    // 启动定时器
    const timerId = setTimeout(() => {
        console.log(`⏰ [自动关闭] 定时器回调执行 - buttonId: ${buttonId}, 当前时间: ${new Date().toISOString()}`);
        console.log(`⏰ [自动关闭] 定时器ID: ${timerId}`);
        try {
            // 自动取消激活，不检查按钮是否仍然激活，因为定时器只有在按钮激活时才会启动
            console.log(`[自动关闭] 按钮 ${buttonId} 自动关闭（${duration}秒后）`);
            
            // 获取按钮元素
            const toggleButton = document.getElementById(`shortcut-${buttonId}`);
            if (!toggleButton) {
                console.error(`[自动关闭] 按钮 ${buttonId} 未找到，无法自动关闭`);
                clearAutoCloseTimer(buttonId);
                return;
            }
            
            // 检查按钮是否仍然处于激活状态
            // 使用全局暴露的函数，避免作用域问题
            const kpsr = window._kpsr;
            if (!kpsr) {
                console.error(`[自动关闭] 全局函数未初始化，无法自动关闭`);
                clearAutoCloseTimer(buttonId);
                return;
            }
            
            const activeButtons = kpsr.getActiveButtons();
            console.log(`[自动关闭] 检查按钮状态 - activeButtons[${buttonId}]:`, activeButtons[buttonId]);
            if (!activeButtons[buttonId]) {
                console.log(`[自动关闭] 按钮 ${buttonId} 已经处于非激活状态，跳过自动关闭`);
                clearAutoCloseTimer(buttonId);
                return;
            }
            
            console.log(`✅ [自动关闭] 按钮 ${buttonId} 仍然处于激活状态，执行自动关闭`);
            
            // 切换状态 - 直接设置为非激活状态
            activeButtons[buttonId] = false;
            kpsr.saveActiveButtons(activeButtons);
            console.log(`✅ [自动关闭] 已更新按钮 ${buttonId} 的状态为未激活`);
            
            // 执行取消激活快捷键
            console.log(`[自动关闭] 执行取消激活快捷键: ${deactivateShortcut}`);
            kpsr.sendShortcutToServer(deactivateShortcut, 'toggle').then(() => {
                console.log(`✅ [自动关闭] 取消激活快捷键执行成功`);
            }).catch((error) => {
                console.error(`❌ [自动关闭] 取消激活快捷键执行失败:`, error);
            });
            
            // 移除倒计时条和脉冲效果
            removeCountdownBar(toggleButton);
            toggleButton.classList.remove('btn-toggle-pulse');
            console.log(`[自动关闭] 已移除倒计时条和脉冲效果`);
            
            // 添加取消激活动画，让用户看到状态变化
            toggleButton.classList.remove('btn-toggle-on-anim', 'btn-toggle-off-anim', 'active');
            void toggleButton.offsetWidth; // 触发重排
            toggleButton.classList.add('btn-toggle-off-anim');
            console.log(`[自动关闭] 已添加取消激活动画`);
            
            // 动画结束后，完全重置按钮状态
            setTimeout(() => {
                toggleButton.classList.remove('btn-toggle-off-anim', 'active');
                // 确保移除所有可能的状态样式
                toggleButton.style.transform = '';
                toggleButton.style.boxShadow = '';
                toggleButton.style.background = '';
                toggleButton.style.color = '';
                console.log(`✅ [自动关闭] 按钮 ${buttonId} 自动关闭完成，UI已重置`);
            }, 300); // 与取消激活动画时长一致
            
            // 清除定时器和剪贴板监听
            clearAutoCloseTimer(buttonId);
            stopClipboardMonitor(buttonId);
            
            console.log(`✅ [自动关闭] 按钮 ${buttonId} 自动关闭流程完成`);
        } catch (error) {
            console.error('[自动关闭] 自动关闭按钮失败:', error);
            // 即使出错也要清除定时器和剪贴板监听
            clearAutoCloseTimer(buttonId);
            stopClipboardMonitor(buttonId);
        }
    }, duration * 1000);  // 转换为毫秒
    
    // 存储定时器ID
    autoCloseTimers[buttonId] = timerId;
    console.log(`✅ [自动关闭] 已为按钮 ${buttonId} 启动自动关闭定时器，将在 ${duration} 秒后自动关闭，定时器ID: ${timerId}`);
    console.log(`✅ [自动关闭] 当前所有定时器:`, Object.keys(autoCloseTimers));
}

// 添加倒计时条
function addCountdownBar(buttonElement, duration) {
    if (!buttonElement) return;
    
    // 移除旧的倒计时条
    removeCountdownBar(buttonElement);
    
    // 创建新的倒计时条
    const countdownBar = document.createElement('div');
    countdownBar.className = 'toggle-countdown-bar';
    countdownBar.style.animation = `toggleCountdown ${duration}s linear forwards`;
    countdownBar.style.width = '100%';
    
    // 添加到按钮
    buttonElement.appendChild(countdownBar);
}

// 移除倒计时条
function removeCountdownBar(buttonElement) {
    if (!buttonElement) return;
    
    const countdownBar = buttonElement.querySelector('.toggle-countdown-bar');
    if (countdownBar) {
        countdownBar.remove();
    }
}

    // 表单操作函数
    window.showAddForm = function() {
        editingButtonId = null;  // 清空编辑ID，确保是新增模式
        const form = document.getElementById('configForm');
        if (form) {
            form.style.display = 'block';
            resetForm();
        }
    };

    window.hideForm = function() {
        const form = document.getElementById('configForm');
        if (form) {
            form.style.display = 'none';
            resetForm();
        }
    };

    function resetForm() {
        document.getElementById('buttonName').value = '';
        document.getElementById('buttonIcon').value = '';
        document.getElementById('actionType').value = 'single';
        document.getElementById('singleShortcut').value = '';
        document.getElementById('activateShortcut').value = '';
        document.getElementById('deactivateShortcut').value = '';
        
        // 重置多次点击配置
        const multiActions = document.getElementById('multiActions');
        if (multiActions) {
            multiActions.innerHTML = `
                <div class="multi-action-item">
                    <label>点击 1</label>
                    <input type="text" placeholder="例如：Ctrl+C">
                </div>
                <div class="multi-action-item">
                    <label>点击 2</label>
                    <input type="text" placeholder="例如：Ctrl+V">
                </div>
            `;
        }
        
        toggleConfigSections();
    }

    window.toggleConfigSections = function() {
        const actionType = document.getElementById('actionType').value;
        
        document.getElementById('singleConfig').style.display = actionType === 'single' ? 'block' : 'none';
        document.getElementById('multiConfig').style.display = actionType === 'multi' ? 'block' : 'none';
        document.getElementById('toggleConfig').style.display = actionType === 'toggle' ? 'block' : 'none';
    };

    window.addMultiAction = function() {
        const multiActions = document.getElementById('multiActions');
        const actionCount = multiActions.children.length + 1;
        
        const actionItem = document.createElement('div');
        actionItem.className = 'multi-action-item';
        actionItem.innerHTML = `
            <label>点击 ${actionCount}</label>
            <input type="text" placeholder="例如：Ctrl+C">
        `;
        
        multiActions.appendChild(actionItem);
    };

    // 编辑按钮
    window.editButton = async function(id) {
        editingButtonId = id;
        
        try {
            const button = await getButtonFromServer(id);
            if (button) {
                document.getElementById('buttonName').value = button.name;
                document.getElementById('buttonIcon').value = button.icon || '';
                document.getElementById('actionType').value = button.type;
                
                if (button.type === 'single') {
                    document.getElementById('singleShortcut').value = button.shortcut || '';
                } else if (button.type === 'multi' && button.multiActions) {
                    // 加载多次点击配置
                    const multiActions = document.getElementById('multiActions');
                    multiActions.innerHTML = ''; // 清空现有内容
                    
                    button.multiActions.forEach((action, index) => {
                        const actionItem = document.createElement('div');
                        actionItem.className = 'multi-action-item';
                        actionItem.innerHTML = `
                            <label>点击 ${index + 1}</label>
                            <input type="text" value="${action.shortcut || ''}" placeholder="例如：Ctrl+C">
                        `;
                        multiActions.appendChild(actionItem);
                    });
                } else if (button.type === 'toggle' && button.toggleActions) {
                    document.getElementById('activateShortcut').value = button.toggleActions.activate || '';
                    document.getElementById('deactivateShortcut').value = button.toggleActions.deactivate || '';
                    // 加载自动关闭时长
                    if (button.autoCloseDuration) {
                        const autoCloseInput = document.getElementById('autoCloseDuration');
                        if (autoCloseInput) {
                            autoCloseInput.value = button.autoCloseDuration;
                        }
                    }
                }
                
                toggleConfigSections();
                document.getElementById('configForm').style.display = 'block';
            }
        } catch (error) {
            showToast('加载按钮失败: ' + error.message);
            editingButtonId = null;
        }
    };

    // 删除按钮
    window.deleteButton = async function(id) {
        if (confirm('确定要删除这个按钮吗？')) {
            try {
                await deleteButtonOnServer(id);
                showToast(CONFIG.SUCCESS_MESSAGES.BUTTON_DELETED);
                await renderSettingsContent();
                await renderShortcutButtons();
            } catch (error) {
                showToast('删除失败: ' + error.message);
            }
        }
    };

    // 保存按钮
    window.saveButton = async function() {
        const name = document.getElementById('buttonName').value.trim();
        const icon = document.getElementById('buttonIcon').value.trim();
        const actionType = document.getElementById('actionType').value;
        
        // 验证按钮名称
        if (!name) {
            showFieldError(document.getElementById('buttonName'), CONFIG.ERROR_MESSAGES.MISSING_NAME);
            return;
        } else {
            hideFieldError(document.getElementById('buttonName'));
        }
        
        if (name.length > CONFIG.VALIDATION.MAX_BUTTON_NAME_LENGTH) {
            showFieldError(document.getElementById('buttonName'), CONFIG.ERROR_MESSAGES.NAME_TOO_LONG);
            return;
        } else {
            hideFieldError(document.getElementById('buttonName'));
        }
        
        // 清理输入数据，防止XSS攻击
        const sanitizedName = sanitizeInput(name);
        const sanitizedIcon = sanitizeInput(icon);
        
        let buttonData = {
            name: sanitizedName,
            icon: sanitizedIcon || '🔘',
            type: actionType
        };
        
        if (actionType === 'single') {
            const shortcut = document.getElementById('singleShortcut').value.trim();
            const validation = validateShortcut(shortcut);
            
            if (!validation.valid) {
                showFieldError(document.getElementById('singleShortcut'), validation.message);
                return;
            } else {
                hideFieldError(document.getElementById('singleShortcut'));
            }
            
            // 使用标准化后的快捷键
            buttonData.shortcut = validation.normalized || normalizeShortcut(shortcut);
            // 清理其他类型的字段
            buttonData.multiActions = undefined;
            buttonData.toggleActions = undefined;
        } else if (actionType === 'multi') {
            const multiInputs = document.querySelectorAll('#multiActions input');
            const actions = [];
            let hasError = false;
            
            multiInputs.forEach((input, index) => {
                const shortcut = input.value.trim();
                if (shortcut) {
                    const validation = validateShortcut(shortcut);
                    if (!validation.valid) {
                        showFieldError(input, validation.message);
                        hasError = true;
                    } else {
                        hideFieldError(input);
                        // 使用标准化后的快捷键
                        actions.push({ shortcut: validation.normalized || normalizeShortcut(shortcut) });
                    }
                } else {
                    hideFieldError(input);
                }
            });
            
            if (hasError) {
                return;
            }
            
            if (actions.length === 0) {
                showToast(CONFIG.ERROR_MESSAGES.MISSING_ACTIONS);
                return;
            }
            
            buttonData.multiActions = actions;
            // 清理其他类型的字段
            buttonData.shortcut = undefined;
            buttonData.toggleActions = undefined;
        } else if (actionType === 'toggle') {
            const activate = document.getElementById('activateShortcut').value.trim();
            const deactivate = document.getElementById('deactivateShortcut').value.trim();
            
            const activateValidation = validateShortcut(activate);
            const deactivateValidation = validateShortcut(deactivate);
            
            if (!activateValidation.valid) {
                showFieldError(document.getElementById('activateShortcut'), activateValidation.message);
                return;
            } else {
                hideFieldError(document.getElementById('activateShortcut'));
            }
            
            if (!deactivateValidation.valid) {
                showFieldError(document.getElementById('deactivateShortcut'), deactivateValidation.message);
                return;
            } else {
                hideFieldError(document.getElementById('deactivateShortcut'));
            }
            
            // 获取自动关闭时长
            const autoCloseInput = document.getElementById('autoCloseDuration');
            let autoCloseDuration = null;
            if (autoCloseInput && autoCloseInput.value.trim()) {
                const duration = parseInt(autoCloseInput.value.trim(), 10);
                if (isNaN(duration) || duration < 0) {
                    showToast('自动关闭时长必须是大于等于0的整数（秒）');
                    return;
                } else {
                    autoCloseDuration = duration === 0 ? null : duration;  // 0表示不自动关闭
                }
            }
            
            buttonData.toggleActions = {
                activate: activateValidation.normalized || normalizeShortcut(activate),
                deactivate: deactivateValidation.normalized || normalizeShortcut(deactivate)
            };
            buttonData.autoCloseDuration = autoCloseDuration;
            // 清理其他类型的字段
            buttonData.shortcut = undefined;
            buttonData.multiActions = undefined;
        }
        
        try {
            if (editingButtonId) {
                // 更新现有按钮
                await updateButtonOnServer(editingButtonId, buttonData);
                showToast(CONFIG.SUCCESS_MESSAGES.BUTTON_UPDATED);
            } else {
                // 添加新按钮
                await saveButtonToServer(buttonData);
                showToast(CONFIG.SUCCESS_MESSAGES.BUTTON_ADDED);
            }
            
            // 刷新界面
            hideForm();
            await renderSettingsContent();
            await renderShortcutButtons();
            
            // 清除编辑ID
            editingButtonId = null;
        } catch (error) {
            showToast('保存失败: ' + error.message);
        }
    };

    // 鼠标按钮相关函数
    window.showMouseAddForm = function() {
        editingMouseButtonId = null;
        currentSequenceKeys = [];  // 重置序列
        
        const form = document.getElementById('mouseConfigForm');
        const list = document.getElementById('mouseButtonList');
        
        // 显示表单，隐藏列表
        form.style.display = 'block';
        list.style.display = 'none';
        
        // 重置表单
        document.getElementById('mouseConfigMode').value = 'single';
        document.getElementById('mouseKeyType').value = 'left';
        document.getElementById('mouseShortcut').value = '';
        toggleMouseConfigMode();
        renderSequenceKeys();
    };

    window.hideMouseForm = function() {
        const form = document.getElementById('mouseConfigForm');
        const list = document.getElementById('mouseButtonList');
        
        // 隐藏表单，显示列表
        form.style.display = 'none';
        list.style.display = 'block';
        
        // 清除编辑ID
        editingMouseButtonId = null;
    };

    window.editMouseButton = async function(id) {
        try {
            // 获取按钮数据
            const button = await getMouseButtonFromServer(id);
            
            if (!button) {
                showToast('按钮不存在');
                return;
            }
            
            // 设置编辑ID
            editingMouseButtonId = id;
            
            // 显示表单，隐藏列表
            const form = document.getElementById('mouseConfigForm');
            const list = document.getElementById('mouseButtonList');
            form.style.display = 'block';
            list.style.display = 'none';
            
            // 判断是序列还是单键
            const modeElem = document.getElementById('mouseConfigMode');
            
            if (button.sequence && Array.isArray(button.sequence) && button.sequence.length > 0) {
                // 序列模式
                modeElem.value = 'sequence';
                currentSequenceKeys = [...button.sequence];
                toggleMouseConfigMode();
                renderSequenceKeys();
            } else {
                // 单键模式
                modeElem.value = 'single';
                currentSequenceKeys = [];
                toggleMouseConfigMode();
                document.getElementById('mouseKeyType').value = button.keyType || 'left';
            }
            
            // 填充快捷键
            document.getElementById('mouseShortcut').value = button.action || '';
            
        } catch (error) {
            showToast('编辑失败: ' + error.message);
        }
    };

    window.deleteMouseButton = async function(id) {
        if (!confirm('确定要删除这个鼠标按钮吗？')) {
            return;
        }
        
        try {
            await deleteMouseButtonOnServer(id);
            showToast('鼠标按钮删除成功');
            
            // 重新加载监听器映射
            try {
                await fetch('/api/mouse-listener/reload', { method: 'POST' });
            } catch (e) {
                Logger.warn('重新加载监听器映射失败:', e);
            }
            
            // 刷新界面
            await renderMouseSettingsContent();
        } catch (error) {
            showToast('删除失败: ' + error.message);
        }
    };

    window.saveMouseButton = async function() {
        Logger.log('saveMouseButton 被调用');
        
        const modeElem = document.getElementById('mouseConfigMode');
        const keyTypeElem = document.getElementById('mouseKeyType');
        const shortcutElem = document.getElementById('mouseShortcut');
        
        const mode = modeElem ? modeElem.value : 'single';
        const shortcut = shortcutElem ? shortcutElem.value.trim() : '';
        
        Logger.log('表单值:', { mode, shortcut, currentSequenceKeys });
        
        // 验证快捷键
        if (!shortcut) {
            showToast('请输入要映射的快捷键');
            return;
        }
        
        // 标准化快捷键格式
        const normalizedShortcut = normalizeShortcut(shortcut);
        Logger.log('标准化快捷键:', normalizedShortcut);
        
        // 验证快捷键格式
        if (!CONFIG.REGEX.SHORTCUT.test(normalizedShortcut)) {
            showToast('快捷键格式不正确，请使用小写字母和+分隔，例如：ctrl+v');
            return;
        }
        
        let buttonData = {
            action: normalizedShortcut
        };
        
        if (mode === 'single') {
            // 单键模式
            const keyType = keyTypeElem ? keyTypeElem.value : null;
            const keyName = MOUSE_KEY_CONFIG[keyType];
            
            if (!keyName) {
                showToast('请选择鼠标按键');
                return;
            }
            
            buttonData.name = sanitizeInput(keyName);
            buttonData.keyType = keyType;
            buttonData.sequence = null;  // 清除序列
        } else {
            // 序列模式
            if (currentSequenceKeys.length < 2) {
                showToast('序列模式至少需要添加2个按键');
                return;
            }
            
            // 生成序列名称
            const sequenceName = currentSequenceKeys.map(k => MOUSE_KEY_CONFIG[k]).join(' → ');
            buttonData.name = sanitizeInput(sequenceName);
            buttonData.sequence = currentSequenceKeys;
            buttonData.keyType = null;  // 清除单键
        }
        
        Logger.log('准备保存的数据:', buttonData);
        
        try {
            if (editingMouseButtonId) {
                // 更新现有按钮
                Logger.log('更新按钮, ID:', editingMouseButtonId);
                await updateMouseButtonOnServer(editingMouseButtonId, buttonData);
                showToast('鼠标按钮更新成功');
            } else {
                // 添加新按钮
                Logger.log('添加新按钮');
                await saveMouseButtonToServer(buttonData);
                showToast('鼠标按钮添加成功');
            }
            
            // 重新加载监听器映射
            try {
                await fetch('/api/mouse-listener/reload', { method: 'POST' });
            } catch (e) {
                Logger.warn('重新加载监听器映射失败:', e);
            }
            
            // 刷新界面
            hideMouseForm();
            await renderMouseSettingsContent();
            
            // 清除编辑ID和序列
            editingMouseButtonId = null;
            currentSequenceKeys = [];
        } catch (error) {
            Logger.error('保存失败:', error);
            showToast('保存失败: ' + error.message);
        }
    };

    // 初始化
    Logger.log('脚本初始化完成');
    Logger.log('侧边栏功能已初始化');
    Logger.log('设置界面渲染功能已初始化');
    Logger.log('表单操作功能已初始化');
    Logger.log('API调用功能已初始化');
    Logger.log('日志工具功能已初始化');
    Logger.log('鼠标按钮功能已初始化');
});

// 清理所有资源（页面卸载时调用）
function cleanupAllResources() {
    console.log('[清理] 开始清理所有资源...');
    
    // 清理所有定时器
    for (const buttonId in autoCloseTimers) {
        if (autoCloseTimers[buttonId]) {
            clearTimeout(autoCloseTimers[buttonId]);
            delete autoCloseTimers[buttonId];
            console.log(`[清理] 已清理按钮 ${buttonId} 的定时器`);
        }
    }
    
    // 清理所有 EventSource 连接
    for (const buttonId in clipboardEventSources) {
        if (clipboardEventSources[buttonId]) {
            clipboardEventSources[buttonId].close();
            delete clipboardEventSources[buttonId];
            console.log(`[清理] 已关闭按钮 ${buttonId} 的 EventSource`);
        }
    }
    
    // 清理按钮引用
    for (const buttonId in clipboardButtonRefs) {
        delete clipboardButtonRefs[buttonId];
    }
    
    console.log('[清理] 资源清理完成');
}

// 页面卸载时清理资源
window.addEventListener('beforeunload', () => {
    cleanupAllResources();
});

// 页面隐藏时也清理（某些情况下 beforeunload 可能不触发）
window.addEventListener('pagehide', () => {
    cleanupAllResources();
});
