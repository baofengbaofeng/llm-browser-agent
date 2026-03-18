// Vue 3 应用 - CDN 版本
// 注意：initialConfig 和 i18n 从 HTML 中注入
const { createApp, ref, computed, onMounted, watch } = Vue;

// 创建应用
const app = createApp({
    setup() {
        // ============ 响应式数据 ============
        const task = ref('');
        const running = ref(false);
        const plans = ref([]);
        const selectedPlanId = ref(null);
        const showSettings = ref(false);
        const showLangPanel = ref(false);
        const showApiKey = ref(false);
        const showSummary = ref(false);
        const logMessages = ref([]);
        const hasResult = ref(false);
        const resultTitle = ref('');
        const resultHeaderClass = ref('');
        const showResultConfig = ref(false);

        // 语言列表
        const languages = ref({
            'zh-hans': '简体中文',
            'zh-hant': '繁體中文',
            'en': 'English',
            'ja': '日本語',
            'ko': '한국어',
            'es': 'Español',
            'pt': 'Português',
            'fr': 'Français',
            'de': 'Deutsch',
            'ru': 'Русский'
        });

        // 当前语言
        const currentLang = ref(document.documentElement.lang || 'zh-hans');

        // 配置数据，初始为空，页面加载后通过AJAX获取
        const config = ref({
            model: '',
            base_url: '',
            api_key: '',
            temperature: 0.1,
            max_actions_per_step: 10,
            llm_timeout: 300,
            max_failures: 5,
            step_timeout: 180,
            calculate_cost: false,
            use_vision: false,
            use_thinking: false,
            fast_mode: false,
            demo_mode: false,
            headless: true,
            enable_security: true,
            use_sandbox: true
        });

        // ============ 计算属性 ============
        const formattedLogs = computed(() => {
            return logMessages.value.map(log => `[${log.time}] ${log.message}`).join('\n');
        });

        const previewTaskContent = computed(() => {
            const plan = plans.value.find(p => p.id === selectedPlanId.value);
            return plan ? plan.task : '';
        });

        // ============ 方法 ============

        // 获取当前语言
        const getCurrentLang = () => {
            const htmlLang = document.documentElement.lang;
            return htmlLang || 'zh-hans';
        };

        // 自动编号行
        const autoNumberLines = () => {
            if (!task.value) return;
            const lines = task.value.split('\n');
            let numberedLines = [];
            
            lines.forEach((line, index) => {
                if (line === undefined) return;
                const trimmedLine = line.trim();
                if (trimmedLine && !/^\d+\./.test(trimmedLine)) {
                    numberedLines.push(`${index + 1}. ${trimmedLine}`);
                } else {
                    numberedLines.push(line);
                }
            });
            
            const newText = numberedLines.join('\n');
            if (task.value !== newText) {
                task.value = newText;
            }
        };

        // 格式化时间
        const formatTime = (timestamp) => {
            if (!timestamp) return '-';
            const date = new Date(timestamp);
            return date.toLocaleString('zh-CN', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        };

        // 加载计划列表
        const loadPlans = async () => {
            try {
                const response = await fetch('/api/customer/task/plan/');
                if (response.ok) {
                    const result = await response.json();
                    if (result.meta && result.meta.code === 0) {
                        plans.value = result.data?.tasks || [];
                    }
                }
            } catch (error) {
                console.error('加载计划失败:', error);
            }
        };

        // 预览计划
        const previewPlan = (plan) => {
            selectedPlanId.value = plan.id;
            task.value = plan.task || '';
            autoNumberLines();
        };

        // 删除任务
        const deletePlan = async (planId, event) => {
            event.stopPropagation();
            if (!confirm(translations.value.CONFIRM_DELETE_PLAN || '确定要删除这个计划吗？')) return;
            
            // 从列表中移除
            plans.value = plans.value.filter(p => p.id !== planId);
            
            // 更新本地存储
            savePlansToStorage();
            
            if (selectedPlanId.value === planId) {
                selectedPlanId.value = null;
                task.value = '';
            }
            
            showNotification(translations.value.PLAN_DELETED_SUCCESS || '计划已删除', 'success');
        };

        // 重置任务
        const resetTask = () => {
            if (confirm(translations.value.CONFIRM_RESET_TASK || '确定要清空当前任务吗？')) {
                task.value = '';
                localStorage.removeItem('llm_browser_agent_task');
            }
        };

        // 保存任务
        const saveTask = async () => {
            if (!task.value || !task.value.trim()) {
                showNotification(translations.value.TASK_EMPTY_WARNING || '任务内容不能为空', 'warning');
                return;
            }

            const firstLine = task.value.split('\n')[0] || '';
            const planName = prompt(
                translations.value.SAVE_PLAN_PROMPT || '请输入计划名称：',
                firstLine.substring(0, 30) || translations.value.UNTITLED_PLAN || '未命名计划'
            );
            
            if (!planName) return;

            // 创建新计划对象
            const newPlan = {
                id: Date.now().toString(),
                task_name: planName,
                task: task.value,
                created_at: new Date().toISOString()
            };

            // 添加到计划列表
            plans.value.unshift(newPlan);
            selectedPlanId.value = newPlan.id;

            // 保存到本地存储
            savePlansToStorage();

            showNotification(translations.value.PLAN_SAVED_SUCCESS || '计划已保存', 'success');
        };

        // 保存计划列表到本地存储
        const savePlansToStorage = () => {
            localStorage.setItem('llm_browser_agent_plans', JSON.stringify(plans.value));
        };

        // 从本地存储加载计划列表
        const loadPlansFromStorage = () => {
            const stored = localStorage.getItem('llm_browser_agent_plans');
            if (stored) {
                try {
                    const parsed = JSON.parse(stored);
                    if (Array.isArray(parsed)) {
                        plans.value = parsed;
                    }
                } catch (e) {
                    console.error('加载本地计划失败:', e);
                }
            }
        };

        // 当前任务ID
        let currentTaskId = null;

        // 运行任务
        const runTask = async () => {
            if (!task.value.trim()) {
                showNotification(translations.value.TASK_EMPTY_WARNING || '请输入任务内容', 'warning');
                return;
            }

            running.value = true;
            logMessages.value = [];
            hasResult.value = true;
            resultHeaderClass.value = 'status-running';
            resultTitle.value = translations.value.STATUS_RUNNING || '执行中...';
            showResultConfig.value = true;

            try {
                const response = await fetch('/api/task/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        task_prompt: task.value,
                        model_name: config.value.model,
                        model_api_url: config.value.base_url,
                        model_api_key: config.value.api_key,
                        model_temperature: config.value.temperature,
                        model_timeout: config.value.llm_timeout,
                        agent_max_actions_per_step: config.value.max_actions_per_step,
                        agent_max_failures: config.value.max_failures,
                        agent_step_timeout: config.value.step_timeout,
                        agent_calculate_cost: config.value.calculate_cost,
                        agent_use_vision: config.value.use_vision,
                        agent_use_thinking: config.value.use_thinking,
                        agent_fast_mode: config.value.fast_mode,
                        agent_demo_mode: config.value.demo_mode,
                        browser_headless: config.value.headless,
                        browser_enable_security: config.value.enable_security,
                        browser_use_sandbox: config.value.use_sandbox
                    })
                });

                if (response.ok) {
                    const result = await response.json();
                    if (result.meta && result.meta.code === 0) {
                        currentTaskId = result.data.task_id;
                        setupEventStream(currentTaskId);
                    } else {
                        throw new Error(result.meta.text || '任务启动失败');
                    }
                } else {
                    throw new Error('任务启动失败');
                }
            } catch (error) {
                console.error('执行任务失败:', error);
                running.value = false;
                resultHeaderClass.value = 'status-error';
                resultTitle.value = translations.value.STATUS_ERROR || '执行失败';
                showNotification(translations.value.TASK_START_ERROR || '启动失败', 'error');
            }
        };

        // 停止任务
        const stopTask = async () => {
            if (!currentTaskId) {
                running.value = false;
                resultHeaderClass.value = 'status-warning';
                resultTitle.value = translations.value.STATUS_STOPPED || '已停止';
                return;
            }

            try {
                const response = await fetch(`/api/task/${currentTaskId}/cancel/`, {
                    method: 'POST'
                });

                if (response.ok) {
                    const result = await response.json();
                    if (result.meta && result.meta.code === 0) {
                        running.value = false;
                        resultHeaderClass.value = 'status-warning';
                        resultTitle.value = translations.value.STATUS_STOPPED || '已停止';
                        showNotification('任务已取消', 'success');
                    }
                }
            } catch (error) {
                console.error('取消任务失败:', error);
                showNotification('取消任务失败', 'error');
            }
        };

        // 设置事件流
        const setupEventStream = (taskId) => {
            const eventSource = new EventSource(`/api/events/${taskId}`);
            
            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleEvent(data);
            };
            
            eventSource.onerror = () => {
                eventSource.close();
                running.value = false;
            };
        };

        // 处理事件
        const handleEvent = (data) => {
            const time = new Date().toLocaleTimeString();
            
            switch (data.type) {
                case 'log':
                    logMessages.value.push({
                        time: time,
                        message: data.message,
                        level: data.level || 'info'
                    });
                    break;
                case 'status':
                    if (data.status === 'completed') {
                        running.value = false;
                        resultHeaderClass.value = 'status-success';
                        resultTitle.value = translations.value.STATUS_SUCCESS || '执行成功';
                    } else if (data.status === 'failed') {
                        running.value = false;
                        resultHeaderClass.value = 'status-error';
                        resultTitle.value = translations.value.STATUS_ERROR || '执行失败';
                    }
                    break;
            }
        };

        // 显示通知
        const showNotification = (message, type = 'info') => {
            const notification = document.createElement('div');
            notification.className = `notification notification-${type}`;
            notification.textContent = message;
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 12px 20px;
                border-radius: 8px;
                color: white;
                font-size: 14px;
                z-index: 10000;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                ${type === 'success' ? 'background: #34c759;' : 
                  type === 'error' ? 'background: #ff3b30;' : 
                  type === 'warning' ? 'background: #ff9500;' : 'background: #0071e3;'}
            `;
            
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 3000);
        };

        // 切换配置
        const toggleConfig = (key) => {
            config.value[key] = !config.value[key];
            saveConfig();
        };

        // 保存配置
        const saveConfig = () => {
            localStorage.setItem('llm_browser_agent_config', JSON.stringify(config.value));
        };

        // 加载保存的配置
        const loadSavedConfig = () => {
            const saved = localStorage.getItem('llm_browser_agent_config');
            if (saved) {
                config.value = { ...config.value, ...JSON.parse(saved) };
            }
        };

        // 加载保存的任务
        const loadSavedTask = () => {
            const saved = localStorage.getItem('llm_browser_agent_task');
            if (saved) {
                task.value = saved;
            }
        };

        // 监听任务变化并保存
        watch(task, (newVal) => {
            localStorage.setItem('llm_browser_agent_task', newVal);
        });

        // 监听配置变化
        watch(config, () => {
            saveConfig();
        }, { deep: true });

        // 翻译数据
        const translations = ref({});

        // 加载语言翻译
        const loadTranslations = async () => {
            try {
                const lang = getCurrentLang();
                const response = await fetch(`/api/language/?lang=${lang}`);
                if (response.ok) {
                    const result = await response.json();
                    if (result.meta && result.meta.code === 0 && result.data) {
                        i18n = result.data;
                        translations.value = result.data;
                    }
                }
            } catch (error) {
                console.error('加载翻译失败:', error);
            }
        };

        // 加载客户任务参数配置
        const loadCustomerConfig = async () => {
            try {
                const response = await fetch('/api/customer/task/args/');
                if (response.ok) {
                    const result = await response.json();
                    if (result.meta && result.meta.code === 0 && result.data) {
                        const data = result.data;
                        config.value = {
                            model: data.model_name || '',
                            base_url: data.model_api_url || '',
                            api_key: data.model_api_key || '',
                            temperature: data.model_temperature || 0.1,
                            max_actions_per_step: data.agent_max_actions_per_step || 10,
                            llm_timeout: data.model_timeout || 300,
                            max_failures: data.agent_max_failures || 5,
                            step_timeout: data.agent_step_timeout || 180,
                            calculate_cost: data.agent_calculate_cost || false,
                            use_vision: data.agent_use_vision || false,
                            use_thinking: data.agent_use_thinking || false,
                            fast_mode: data.agent_fast_mode || false,
                            demo_mode: data.agent_demo_mode || false,
                            headless: data.browser_headless !== undefined ? data.browser_headless : true,
                            enable_security: data.browser_enable_security !== undefined ? data.browser_enable_security : true,
                            use_sandbox: data.browser_use_sandbox !== undefined ? data.browser_use_sandbox : true
                        };
                    }
                }
            } catch (error) {
                console.error('加载客户配置失败:', error);
            }
        };

        // ============ 生命周期 ============
        onMounted(async () => {
            await loadTranslations();
            await loadCustomerConfig();
            loadPlansFromStorage();
            loadSavedConfig();
            loadSavedTask();
            autoNumberLines();
        });

        // ============ 返回模板需要的数据和方法 ============
        return {
            // 数据
            task,
            running,
            plans,
            selectedPlanId,
            showSettings,
            showLangPanel,
            showApiKey,
            showSummary,
            config,
            logMessages,
            hasResult,
            resultTitle,
            resultHeaderClass,
            showResultConfig,
            formattedLogs,
            previewTaskContent,
            translations,
            languages,
            currentLang,

            // 方法
            autoNumberLines,
            formatTime,
            previewPlan,
            deletePlan,
            resetTask,
            saveTask,
            runTask,
            stopTask,
            toggleConfig
        };
    }
});

// 挂载应用
app.mount('#app');
