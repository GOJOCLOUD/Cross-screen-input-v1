// 应用常量和配置

const CONFIG = {
    // API端点
    API_ENDPOINTS: {
        LIST: '/api/button-config/list',
        ADD: '/api/button-config/add',
        UPDATE: '/api/button-config/update',
        DELETE: '/api/button-config/delete',
        GET: '/api/button-config/get',
        EXECUTE: '/api/shortcut/execute',
        MOUSE_LIST: '/api/mouse-config/list',
        MOUSE_ADD: '/api/mouse-config/add',
        MOUSE_UPDATE: '/api/mouse-config/update',
        MOUSE_DELETE: '/api/mouse-config/delete',
        MOUSE_GET: '/api/mouse-config/get',
        MOUSE_EXECUTE: '/api/mouse/execute'
    },
    
    // 按钮类型
    BUTTON_TYPES: {
        SINGLE: 'single',
        MULTI: 'multi',
        TOGGLE: 'toggle'
    },
    
    // 验证规则
    VALIDATION: {
        MAX_BUTTON_NAME_LENGTH: 20,
        MAX_BUTTONS: 50,
        CACHE_TIME: 5 * 60 * 1000,  // 5分钟
        DEBOUNCE_DELAY: 300,        // 防抖延迟
        THROTTLE_LIMIT: 100          // 节流限制
    },
    
    // 正则表达式
    REGEX: {
        SHORTCUT: /^([a-z0-9_]+(\+[a-z0-9_]+)*)$/
    },
    
    // 错误消息
    ERROR_MESSAGES: {
        MISSING_NAME: '请输入按钮名称',
        NAME_TOO_LONG: '按钮名称不能超过20个字符',
        MISSING_SHORTCUT: '请输入快捷键',
        INVALID_SHORTCUT: '快捷键格式不正确，请使用小写字母和+分隔，例如：ctrl+v',
        MISSING_ACTIONS: '请至少添加一个点击动作',
        MISSING_TOGGLE_ACTIONS: '请输入激活和取消激活的快捷键',
        NETWORK_ERROR: '网络连接失败，请检查网络',
        SERVER_ERROR: '服务器错误，请稍后重试',
        MISSING_MOUSE_ACTION: '请输入鼠标操作',
        INVALID_MOUSE_ACTION: '鼠标操作格式不正确，请使用小写字母和+分隔，例如：left, ctrl+left'
    },
    
    // 成功消息
    SUCCESS_MESSAGES: {
        BUTTON_ADDED: '按钮添加成功',
        BUTTON_UPDATED: '按钮更新成功',
        BUTTON_DELETED: '按钮已删除',
        SHORTCUT_EXECUTED: '快捷键执行成功',
        MOUSE_BUTTON_ADDED: '鼠标按钮添加成功',
        MOUSE_BUTTON_UPDATED: '鼠标按钮更新成功',
        MOUSE_BUTTON_DELETED: '鼠标按钮已删除',
        MOUSE_EXECUTED: '鼠标操作执行成功'
    }
};

// 导出常量
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
} else if (typeof window !== 'undefined') {
    window.CONFIG = CONFIG;
}
