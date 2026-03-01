// 设置管理模块
// 处理快捷键和鼠标按钮的设置管理

class SettingsManager {
    constructor() {
        this.shortcutButtons = [];
        this.mouseButtons = [];
        this.currentView = 'shortcut'; // 'shortcut' 或 'mouse'
        this.isEditing = false;
        this.editingId = null;
    }
    
    /**
     * 加载快捷键按钮
     */
    async loadShortcutButtons() {
        try {
            const response = await window.networkRequest.get('/api/button-config/list');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.shortcutButtons = data.buttons || [];
                return this.shortcutButtons;
            }
            
            console.error('[SettingsManager] 加载快捷键按钮失败:', data);
            return [];
        } catch (error) {
            console.error('[SettingsManager] 加载快捷键按钮出错:', error);
            return [];
        }
    }
    
    /**
     * 加载鼠标按钮
     */
    async loadMouseButtons() {
        try {
            const response = await window.networkRequest.get('/api/mouse-config/list');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.mouseButtons = data.buttons || [];
                return this.mouseButtons;
            }
            
            console.error('[SettingsManager] 加载鼠标按钮失败:', data);
            return [];
        } catch (error) {
            console.error('[SettingsManager] 加载鼠标按钮出错:', error);
            return [];
        }
    }
    
    /**
     * 保存快捷键按钮
     */
    async saveShortcutButton(buttonData) {
        try {
            let response;
            
            if (this.editingId && this.editingId === buttonData.id) {
                // 更新现有按钮
                response = await window.networkRequest.put(`/api/button-config/update/${buttonData.id}`, buttonData);
            } else {
                // 添加新按钮
                response = await window.networkRequest.post('/api/button-config/add', buttonData);
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // 重新加载按钮列表
                await this.loadShortcutButtons();
                return true;
            }
            
            throw new Error(data.message || '保存失败');
        } catch (error) {
            console.error('[SettingsManager] 保存快捷键按钮失败:', error);
            throw error;
        }
    }
    
    /**
     * 保存鼠标按钮
     */
    async saveMouseButton(buttonData) {
        try {
            let response;
            
            if (this.editingId && this.editingId === buttonData.id) {
                // 更新现有按钮
                response = await window.networkRequest.put(`/api/mouse-config/update/${buttonData.id}`, buttonData);
            } else {
                // 添加新按钮
                response = await window.networkRequest.post('/api/mouse-config/add', buttonData);
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // 重新加载按钮列表
                await this.loadMouseButtons();
                return true;
            }
            
            throw new Error(data.message || '保存失败');
        } catch (error) {
            console.error('[SettingsManager] 保存鼠标按钮失败:', error);
            throw error;
        }
    }
    
    /**
     * 删除快捷键按钮
     */
    async deleteShortcutButton(buttonId) {
        try {
            const response = await window.networkRequest.delete(`/api/button-config/delete/${buttonId}`);
            const data = await response.json();
            
            if (data.status === 'success') {
                // 重新加载按钮列表
                await this.loadShortcutButtons();
                return true;
            }
            
            throw new Error(data.message || '删除失败');
        } catch (error) {
            console.error('[SettingsManager] 删除快捷键按钮失败:', error);
            throw error;
        }
    }
    
    /**
     * 删除鼠标按钮
     */
    async deleteMouseButton(buttonId) {
        try {
            const response = await window.networkRequest.delete(`/api/mouse-config/delete/${buttonId}`);
            const data = await response.json();
            
            if (data.status === 'success') {
                // 重新加载按钮列表
                await this.loadMouseButtons();
                return true;
            }
            
            throw new Error(data.message || '删除失败');
        } catch (error) {
            console.error('[SettingsManager] 删除鼠标按钮失败:', error);
            throw error;
        }
    }
    
    /**
     * 验证按钮数据
     */
    validateButtonData(buttonData) {
        const errors = [];
        
        // 检查名称
        if (!buttonData.name || buttonData.name.trim() === '') {
            errors.push('按钮名称不能为空');
        }
        
        // 检查类型
        if (!['single', 'multi', 'toggle'].includes(buttonData.type)) {
            errors.push('按钮类型必须是 single、multi 或 toggle');
        }
        
        // 根据类型检查特定字段
        if (buttonData.type === 'single') {
            if (!buttonData.shortcut) {
                errors.push('单次点击按钮必须设置快捷键');
            }
        } else if (buttonData.type === 'multi') {
            if (!buttonData.multiActions || buttonData.multiActions.length === 0) {
                errors.push('多次点击按钮必须设置动作列表');
            }
        } else if (buttonData.type === 'toggle') {
            if (!buttonData.toggleActions || buttonData.toggleActions.length === 0) {
                errors.push('激活模式按钮必须设置动作列表');
            }
        }
        
        return {
            isValid: errors.length === 0,
            errors: errors
        };
    }
    
    /**
     * 创建设置界面
     */
    createSettingsInterface(container) {
        container.innerHTML = `
            <div class="settings-container">
                <div class="settings-header">
                    <div class="tab-buttons">
                        <button id="shortcutTab" class="tab-btn active">快捷键</button>
                        <button id="mouseTab" class="tab-btn">鼠标按键</button>
                    </div>
                    <div class="header-actions">
                        <button id="addButtonBtn" class="add-btn">
                            <span class="icon">+</span>
                            添加按钮
                        </button>
                    </div>
                </div>
                
                <div class="settings-content">
                    <div id="shortcutContent" class="tab-content">
                        <div class="button-list" id="shortcutList">
                            <div class="empty-state">
                                <p>加载中...</p>
                            </div>
                        </div>
                    </div>
                    
                    <div id="mouseContent" class="tab-content hidden">
                        <div class="button-list" id="mouseList">
                            <div class="empty-state">
                                <p>加载中...</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div id="editForm" class="edit-form hidden">
                    <div class="form-header">
                        <h3 id="formTitle">添加按钮</h3>
                        <button id="cancelEditBtn" class="cancel-btn">取消</button>
                    </div>
                    <div class="form-content" id="formContent">
                        <!-- 表单内容将动态生成 -->
                    </div>
                    <div class="form-actions">
                        <button id="saveButtonBtn" class="save-btn">保存</button>
                    </div>
                </div>
            </div>
        `;
        
        // 添加样式
        this.addSettingsStyles();
        
        // 绑定事件
        this.bindSettingsEvents();
        
        // 加载数据
        this.loadInitialData();
        
        // 返回控制对象
        return {
            switchToShortcuts: () => {
                this.switchTab('shortcut');
            },
            switchToMouse: () => {
                this.switchTab('mouse');
            },
            addButton: () => {
                this.showEditForm();
            },
            refresh: () => {
                this.loadInitialData();
            },
            getButtons: () => {
                return this.currentView === 'shortcut' ? this.shortcutButtons : this.mouseButtons;
            }
        };
    }
    
    /**
     * 添加设置界面样式
     */
    addSettingsStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .settings-container {
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            
            .settings-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding-bottom: 16px;
                border-bottom: 1px solid #eee;
            }
            
            .tab-buttons {
                display: flex;
                gap: 12px;
            }
            
            .tab-btn {
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                background: #f0f0f0;
                color: #666;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .tab-btn.active {
                background: #007AFF;
                color: white;
            }
            
            .tab-btn:hover:not(.active) {
                background: #e0e0e0;
            }
            
            .add-btn {
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 8px 16px;
                border: 1px solid #007AFF;
                border-radius: 6px;
                background: white;
                color: #007AFF;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .add-btn:hover {
                background: #007AFF;
                color: white;
            }
            
            .icon {
                font-size: 18px;
                font-weight: bold;
            }
            
            .settings-content {
                position: relative;
            }
            
            .tab-content {
                display: block;
            }
            
            .tab-content.hidden {
                display: none;
            }
            
            .button-list {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                gap: 16px;
                margin-bottom: 20px;
            }
            
            .button-item {
                background: white;
                border-radius: 8px;
                padding: 16px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                transition: all 0.2s ease;
            }
            
            .button-item:hover {
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                transform: translateY(-2px);
            }
            
            .button-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
            }
            
            .button-name {
                font-size: 16px;
                font-weight: 600;
                color: #333;
            }
            
            .button-actions {
                display: flex;
                gap: 8px;
            }
            
            .action-btn {
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .action-btn.edit {
                background: #007AFF;
                color: white;
            }
            
            .action-btn.edit:hover {
                background: #0056CC;
            }
            
            .action-btn.delete {
                background: #FF3B30;
                color: white;
            }
            
            .action-btn.delete:hover {
                background: #D70015;
            }
            
            .button-type {
                font-size: 12px;
                color: #666;
                margin-top: 4px;
            }
            
            .empty-state {
                grid-column: 1 / -1;
                text-align: center;
                padding: 40px 20px;
                color: #999;
            }
            
            .edit-form {
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
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            
            .form-content {
                background: white;
                border-radius: 12px;
                padding: 24px;
                max-width: 500px;
                width: 90%;
                max-height: 80vh;
                overflow-y: auto;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
                transform: scale(0.9);
                transition: transform 0.3s ease;
            }
            
            .form-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding-bottom: 16px;
                border-bottom: 1px solid #eee;
            }
            
            .form-header h3 {
                margin: 0;
                font-size: 18px;
                font-weight: 600;
                color: #333;
            }
            
            .cancel-btn {
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                background: #f0f0f0;
                color: #666;
                font-size: 14px;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .cancel-btn:hover {
                background: #e0e0e0;
            }
            
            .save-btn {
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                background: #007AFF;
                color: white;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .save-btn:hover {
                background: #0056CC;
            }
            
            .form-group {
                margin-bottom: 16px;
            }
            
            .form-group label {
                display: block;
                font-size: 14px;
                font-weight: 500;
                color: #333;
                margin-bottom: 8px;
            }
            
            .form-group input,
            .form-group select,
            .form-group textarea {
                width: 100%;
                padding: 10px 12px;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 14px;
                transition: border-color 0.2s ease;
            }
            
            .form-group input:focus,
            .form-group select:focus,
            .form-group textarea:focus {
                outline: none;
                border-color: #007AFF;
                box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1);
            }
            
            .form-actions {
                text-align: right;
                margin-top: 24px;
            }
        `;
        
        document.head.appendChild(style);
    }
    
    /**
     * 绑定设置界面事件
     */
    bindSettingsEvents() {
        // 标签页切换
        document.getElementById('shortcutTab').addEventListener('click', () => {
            this.switchTab('shortcut');
        });
        
        document.getElementById('mouseTab').addEventListener('click', () => {
            this.switchTab('mouse');
        });
        
        // 添加按钮
        document.getElementById('addButtonBtn').addEventListener('click', () => {
            this.showEditForm();
        });
        
        // 取消编辑
        document.getElementById('cancelEditBtn').addEventListener('click', () => {
            this.hideEditForm();
        });
        
        // 保存按钮
        document.getElementById('saveButtonBtn').addEventListener('click', () => {
            this.saveCurrentEdit();
        });
    }
    
    /**
     * 切换标签页
     */
    switchTab(tab) {
        this.currentView = tab;
        
        // 更新标签页按钮状态
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        if (tab === 'shortcut') {
            document.getElementById('shortcutTab').classList.add('active');
            document.getElementById('shortcutContent').classList.remove('hidden');
            document.getElementById('mouseContent').classList.add('hidden');
        } else {
            document.getElementById('mouseTab').classList.add('active');
            document.getElementById('shortcutContent').classList.add('hidden');
            document.getElementById('mouseContent').classList.remove('hidden');
        }
    }
    
    /**
     * 加载初始数据
     */
    async loadInitialData() {
        await this.loadShortcutButtons();
        await this.loadMouseButtons();
        this.renderButtonList();
    }
    
    /**
     * 渲染按钮列表
     */
    renderButtonList() {
        const shortcutList = document.getElementById('shortcutList');
        const mouseList = document.getElementById('mouseList');
        
        const buttons = this.currentView === 'shortcut' ? this.shortcutButtons : this.mouseButtons;
        const targetList = this.currentView === 'shortcut' ? shortcutList : mouseList;
        
        if (buttons.length === 0) {
            targetList.innerHTML = '<div class="empty-state"><p>暂无按钮，点击上方添加</p></div>';
            return;
        }
        
        let html = '';
        buttons.forEach(button => {
            html += this.createButtonHTML(button);
        });
        
        targetList.innerHTML = html;
        
        // 绑定按钮事件
        this.bindButtonEvents();
    }
    
    /**
     * 创建按钮HTML
     */
    createButtonHTML(button) {
        return `
            <div class="button-item" data-id="${button.id}">
                <div class="button-header">
                    <div class="button-name">${button.name}</div>
                    <div class="button-actions">
                        <button class="action-btn edit" data-id="${button.id}">编辑</button>
                        <button class="action-btn delete" data-id="${button.id}">删除</button>
                    </div>
                </div>
                <div class="button-type">${this.getTypeLabel(button.type)}</div>
            </div>
        `;
    }
    
    /**
     * 获取类型标签
     */
    getTypeLabel(type) {
        const labels = {
            single: '单次点击',
            multi: '多次点击',
            toggle: '激活模式'
        };
        return labels[type] || type;
    }
    
    /**
     * 绑定按钮事件
     */
    bindButtonEvents() {
        // 编辑按钮
        document.querySelectorAll('.action-btn.edit').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const buttonId = e.target.getAttribute('data-id');
                this.editButton(buttonId);
            });
        });
        
        // 删除按钮
        document.querySelectorAll('.action-btn.delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const buttonId = e.target.getAttribute('data-id');
                this.deleteButton(buttonId);
            });
        });
    }
    
    /**
     * 显示编辑表单
     */
    showEditForm(buttonData = null) {
        const editForm = document.getElementById('editForm');
        const formTitle = document.getElementById('formTitle');
        const formContent = document.getElementById('formContent');
        
        this.isEditing = !!buttonData;
        this.editingId = buttonData ? buttonData.id : null;
        
        if (buttonData) {
            formTitle.textContent = '编辑按钮';
        } else {
            formTitle.textContent = '添加按钮';
            buttonData = this.getDefaultButtonData();
        }
        
        formContent.innerHTML = this.createFormHTML(buttonData);
        
        // 显示表单
        editForm.classList.remove('hidden');
        setTimeout(() => {
            editForm.style.opacity = '1';
            document.querySelector('.form-content').style.transform = 'scale(1)';
        }, 10);
    }
    
    /**
     * 隐藏编辑表单
     */
    hideEditForm() {
        const editForm = document.getElementById('editForm');
        
        editForm.style.opacity = '0';
        document.querySelector('.form-content').style.transform = 'scale(0.9)';
        
        setTimeout(() => {
            editForm.classList.add('hidden');
        }, 300);
    }
    
    /**
     * 获取默认按钮数据
     */
    getDefaultButtonData() {
        return {
            name: '',
            type: 'single',
            shortcut: '',
            multiActions: [],
            toggleActions: []
        };
    }
    
    /**
     * 创建表单HTML
     */
    createFormHTML(buttonData) {
        let html = `
            <div class="form-group">
                <label for="buttonName">按钮名称</label>
                <input type="text" id="buttonName" value="${buttonData.name || ''}" placeholder="请输入按钮名称">
            </div>
            
            <div class="form-group">
                <label for="buttonType">按钮类型</label>
                <select id="buttonType">
                    <option value="single" ${buttonData.type === 'single' ? 'selected' : ''}>单次点击</option>
                    <option value="multi" ${buttonData.type === 'multi' ? 'selected' : ''}>多次点击</option>
                    <option value="toggle" ${buttonData.type === 'toggle' ? 'selected' : ''}>激活模式</option>
                </select>
            </div>
        `;
        
        // 根据类型添加特定字段
        if (buttonData.type === 'single') {
            html += `
                <div class="form-group">
                    <label for="shortcut">快捷键</label>
                    <input type="text" id="shortcut" value="${buttonData.shortcut || ''}" placeholder="例如: ctrl+c">
                </div>
            `;
        } else if (buttonData.type === 'multi') {
            html += `
                <div class="form-group">
                    <label>多次点击动作</label>
                    <div id="multiActions">
                        ${this.createMultiActionsHTML(buttonData.multiActions || [])}
                    </div>
                    <button type="button" id="addMultiAction" class="add-btn">添加动作</button>
                </div>
            `;
        } else if (buttonData.type === 'toggle') {
            html += `
                <div class="form-group">
                    <label>激活模式动作</label>
                    <div id="toggleActions">
                        ${this.createToggleActionsHTML(buttonData.toggleActions || [])}
                    </div>
                    <button type="button" id="addToggleAction" class="add-btn">添加动作</button>
                </div>
            `;
        }
        
        return html;
    }
    
    /**
     * 创建多次点击动作HTML
     */
    createMultiActionsHTML(actions) {
        let html = '';
        
        if (actions.length === 0) {
            actions = [{ shortcut: '', count: 1 }];
        }
        
        actions.forEach((action, index) => {
            html += `
                <div class="multi-action-item" data-index="${index}">
                    <input type="text" placeholder="快捷键" value="${action.shortcut || ''}" class="action-shortcut">
                    <input type="number" placeholder="点击次数" value="${action.count || 1}" min="1" max="10" class="action-count">
                    <button type="button" class="action-remove" data-index="${index}">删除</button>
                </div>
            `;
        });
        
        return html;
    }
    
    /**
     * 创建激活模式动作HTML
     */
    createToggleActionsHTML(actions) {
        let html = '';
        
        if (actions.length === 0) {
            actions = [{ shortcut: '', name: '激活' }, { shortcut: '', name: '取消激活' }];
        }
        
        actions.forEach((action, index) => {
            html += `
                <div class="toggle-action-item" data-index="${index}">
                    <input type="text" placeholder="快捷键" value="${action.shortcut || ''}" class="action-shortcut">
                    <input type="text" placeholder="动作名称" value="${action.name || ''}" class="action-name">
                    <button type="button" class="action-remove" data-index="${index}">删除</button>
                </div>
            `;
        });
        
        return html;
    }
    
    /**
     * 编辑按钮
     */
    editButton(buttonId) {
        const buttons = this.currentView === 'shortcut' ? this.shortcutButtons : this.mouseButtons;
        const button = buttons.find(b => b.id === buttonId);
        
        if (button) {
            this.showEditForm(button);
        }
    }
    
    /**
     * 删除按钮
     */
    async deleteButton(buttonId) {
        const confirmed = await UIComponents.showConfirmDialog('确定要删除这个按钮吗？');
        
        if (!confirmed) return;
        
        try {
            if (this.currentView === 'shortcut') {
                await this.deleteShortcutButton(buttonId);
            } else {
                await this.deleteMouseButton(buttonId);
            }
            
            UIComponents.showToast('删除成功', 'success');
        } catch (error) {
            UIComponents.showToast('删除失败: ' + error.message, 'error');
        }
    }
    
    /**
     * 保存当前编辑
     */
    async saveCurrentEdit() {
        const buttonData = this.collectFormData();
        
        // 验证数据
        const validation = this.validateButtonData(buttonData);
        
        if (!validation.isValid) {
            UIComponents.showToast('数据验证失败: ' + validation.errors.join(', '), 'error');
            return;
        }
        
        try {
            if (this.currentView === 'shortcut') {
                await this.saveShortcutButton(buttonData);
            } else {
                await this.saveMouseButton(buttonData);
            }
            
            this.hideEditForm();
            this.renderButtonList();
            UIComponents.showToast('保存成功', 'success');
        } catch (error) {
            UIComponents.showToast('保存失败: ' + error.message, 'error');
        }
    }
    
    /**
     * 收集表单数据
     */
    collectFormData() {
        const name = document.getElementById('buttonName').value.trim();
        const type = document.getElementById('buttonType').value;
        
        const buttonData = {
            name,
            type
        };
        
        if (type === 'single') {
            buttonData.shortcut = document.getElementById('shortcut').value.trim();
        } else if (type === 'multi') {
            buttonData.multiActions = this.collectMultiActions();
        } else if (type === 'toggle') {
            buttonData.toggleActions = this.collectToggleActions();
        }
        
        return buttonData;
    }
    
    /**
     * 收集多次点击动作
     */
    collectMultiActions() {
        const actions = [];
        const actionItems = document.querySelectorAll('.multi-action-item');
        
        actionItems.forEach(item => {
            const shortcut = item.querySelector('.action-shortcut').value.trim();
            const count = parseInt(item.querySelector('.action-count').value) || 1;
            
            if (shortcut) {
                actions.push({ shortcut, count });
            }
        });
        
        return actions;
    }
    
    /**
     * 收集激活模式动作
     */
    collectToggleActions() {
        const actions = [];
        const actionItems = document.querySelectorAll('.toggle-action-item');
        
        actionItems.forEach(item => {
            const shortcut = item.querySelector('.action-shortcut').value.trim();
            const name = item.querySelector('.action-name').value.trim();
            
            if (shortcut && name) {
                actions.push({ shortcut, name });
            }
        });
        
        return actions;
    }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SettingsManager;
} else {
    window.SettingsManager = SettingsManager;
}