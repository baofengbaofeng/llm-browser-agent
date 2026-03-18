-- 数据库DDL脚本，适用于MySQL 8.0+，布尔类型使用TINYINT(1)存储

-- -----------------------------------------------------------------------------
-- 表：llm_browser_agent_task_project
-- 说明：存储任务执行计划（任务模板）及完整配置快照
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS llm_browser_agent_task_project;

CREATE TABLE IF NOT EXISTS llm_browser_agent_task_project
(
    id                         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '主键，自增ID',
    customer_id                VARCHAR(255)        NOT NULL DEFAULT '' COMMENT '客户唯一标识符',
    task_digest                VARCHAR(100)        NOT NULL DEFAULT '' COMMENT '任务摘要',
    task_prompt                TEXT                         DEFAULT NULL COMMENT '任务描述提示词',

    -- 大模型配置
    model_name                 VARCHAR(100)        NOT NULL DEFAULT '' COMMENT '大语言模型名称',
    model_temperature          DECIMAL(2, 1)       NOT NULL DEFAULT 0.1 COMMENT '随机因子',
    model_top_p                DECIMAL(2, 1)       NOT NULL DEFAULT 0.9 COMMENT '采样参数',
    model_api_url              VARCHAR(255)        NOT NULL DEFAULT '' COMMENT '大语言模型API服务地址',
    model_api_key              VARCHAR(255)        NOT NULL DEFAULT '' COMMENT 'API认证密钥',
    model_timeout              INT UNSIGNED        NOT NULL DEFAULT 300 COMMENT 'LLM请求超时时间，单位为秒',

    -- 智能体配置
    agent_use_vision           TINYINT(1) UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用视觉能力：1-是, 0-否',
    agent_max_actions_per_step INT UNSIGNED        NOT NULL DEFAULT 10 COMMENT '单步最大操作数限制',
    agent_max_failures         INT UNSIGNED        NOT NULL DEFAULT 5 COMMENT '最大连续失败次数，超过则终止任务',
    agent_step_timeout         INT UNSIGNED        NOT NULL DEFAULT 180 COMMENT '单步执行超时时间，单位为秒',
    agent_use_thinking         TINYINT(1) UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否启用思考模式：1-是, 0-否',
    agent_calculate_cost       TINYINT(1) UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否启用成本计算：1-是, 0-否',
    agent_fast_mode            TINYINT(1) UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否启用快速模式：1-是, 0-否',
    agent_demo_mode            TINYINT(1) UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否启用演示模式：1-是, 0-否',

    -- 浏览器配置
    browser_headless           TINYINT(1) UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用无头模式：1-是, 0-否',
    browser_enable_security    TINYINT(1) UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用浏览器安全功能：1-是, 0-否',
    browser_use_sandbox        TINYINT(1) UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用浏览器沙箱模式：1-是, 0-否',

    -- 审计字段
    created_at                 TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    created_by                 VARCHAR(255)        NOT NULL DEFAULT '' COMMENT '创建者标识',
    updated_at                 TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    updated_by                 VARCHAR(255)        NOT NULL DEFAULT '' COMMENT '最后更新者标识'
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  auto_increment = 10000000 COMMENT ='任务执行计划表';

-- -----------------------------------------------------------------------------
-- 索引：llm_browser_agent_task_project
-- -----------------------------------------------------------------------------
CREATE INDEX idx_customer_id ON llm_browser_agent_task_project (customer_id);
CREATE INDEX idx_task_project_created_by ON llm_browser_agent_task_project (created_by);
CREATE INDEX idx_task_project_updated_by ON llm_browser_agent_task_project (updated_by);

-- -----------------------------------------------------------------------------
-- 表：llm_browser_agent_customer_profile
-- 说明：存储客户基础信息（Profile）
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS llm_browser_agent_customer_profile;

CREATE TABLE IF NOT EXISTS llm_browser_agent_customer_profile
(
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '主键，自增ID',
    customer_id VARCHAR(255) NOT NULL DEFAULT '' COMMENT '客户唯一标识符',

    -- 审计字段
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    created_by  VARCHAR(255) NOT NULL DEFAULT '' COMMENT '创建者标识',
    updated_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    updated_by  VARCHAR(255) NOT NULL DEFAULT '' COMMENT '最后更新者标识',

    -- 约束
    UNIQUE KEY unk_customer_id (customer_id)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  auto_increment = 10000000 COMMENT ='客户基础信息表';

-- -----------------------------------------------------------------------------
-- 索引：llm_browser_agent_customer_profile
-- -----------------------------------------------------------------------------
CREATE INDEX idx_customer_profile_id ON llm_browser_agent_customer_profile (customer_id);

-- -----------------------------------------------------------------------------
-- 表：llm_browser_agent_customer_setting
-- 说明：存储客户配置设置历史（版本化，每次保存新增记录）
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS llm_browser_agent_customer_setting;

CREATE TABLE IF NOT EXISTS llm_browser_agent_customer_setting
(
    id                         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '主键，自增ID',
    customer_id                VARCHAR(255)        NOT NULL DEFAULT '' COMMENT '客户唯一标识符',
    snapshot_id                INT UNSIGNED        NOT NULL DEFAULT 1 COMMENT '配置快照ID，从1开始递增',

    -- 模型配置
    model_name                 VARCHAR(100)        NOT NULL DEFAULT '' COMMENT '大语言模型名称',
    model_temperature          DECIMAL(2, 1)       NOT NULL DEFAULT 0.1 COMMENT '随机因子',
    model_top_p                DECIMAL(2, 1)       NOT NULL DEFAULT 0.9 COMMENT '采样参数',
    model_api_url              VARCHAR(255)        NOT NULL DEFAULT '' COMMENT '大语言模型API服务地址',
    model_api_key              VARCHAR(255)        NOT NULL DEFAULT '' COMMENT 'API认证密钥',
    model_timeout              INT UNSIGNED        NOT NULL DEFAULT 300 COMMENT 'LLM请求超时时间，单位为秒',

    -- 智能体配置
    agent_use_vision           TINYINT(1) UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用视觉能力：1-是, 0-否',
    agent_max_actions_per_step INT UNSIGNED        NOT NULL DEFAULT 10 COMMENT '单步最大操作数限制',
    agent_max_failures         INT UNSIGNED        NOT NULL DEFAULT 5 COMMENT '最大连续失败次数',
    agent_step_timeout         INT UNSIGNED        NOT NULL DEFAULT 180 COMMENT '单步执行超时时间，单位为秒',
    agent_use_thinking         TINYINT(1) UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否启用思考模式：1-是, 0-否',
    agent_calculate_cost       TINYINT(1) UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否启用成本计算：1-是, 0-否',
    agent_fast_mode            TINYINT(1) UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否启用快速模式：1-是, 0-否',
    agent_demo_mode            TINYINT(1) UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否启用演示模式：1-是, 0-否',

    -- 浏览器配置
    browser_headless           TINYINT(1) UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用无头模式：1-是, 0-否',
    browser_enable_security    TINYINT(1) UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用浏览器安全功能：1-是, 0-否',
    browser_use_sandbox        TINYINT(1) UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用浏览器沙箱模式：1-是, 0-否',

    -- 审计字段
    created_at                 TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    created_by                 VARCHAR(255)        NOT NULL DEFAULT '' COMMENT '创建者标识',
    updated_at                 TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录最后更新时间',
    updated_by                 VARCHAR(255)        NOT NULL DEFAULT '' COMMENT '最后更新者标识'
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  auto_increment = 10000000 COMMENT ='客户配置设置历史表';

-- -----------------------------------------------------------------------------
-- 索引与约束：llm_browser_agent_customer_setting
-- -----------------------------------------------------------------------------
CREATE INDEX idx_customer_setting_customer_id ON llm_browser_agent_customer_setting (customer_id);
CREATE UNIQUE INDEX uq_customer_setting_customer_snapshot
    ON llm_browser_agent_customer_setting (customer_id, snapshot_id);

-- -----------------------------------------------------------------------------
-- 表：llm_browser_agent_task_history
-- 说明：存储任务执行历史记录，包含提交参数、执行结果和耗时
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS llm_browser_agent_task_history;

CREATE TABLE IF NOT EXISTS llm_browser_agent_task_history
(
    id                         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '主键，自增ID',
    customer_id                VARCHAR(255)        NOT NULL DEFAULT '' COMMENT '客户唯一标识符',

    -- 任务提交参数（提示词内容字符串）
    task_id                    VARCHAR(255)        NOT NULL DEFAULT '' COMMENT '任务唯一标识符（UUID）',
    task_prompt                TEXT                         DEFAULT NULL COMMENT '任务提示词内容，存储原始字符串',

    -- 模型配置快照
    model_name                 VARCHAR(100)        NOT NULL DEFAULT '' COMMENT '大语言模型名称',
    model_temperature          DECIMAL(2, 1)       NOT NULL DEFAULT 0.1 COMMENT '随机因子',
    model_top_p                DECIMAL(2, 1)       NOT NULL DEFAULT 0.9 COMMENT '采样参数',
    model_api_url              VARCHAR(255)        NOT NULL DEFAULT '' COMMENT '大语言模型API服务地址',
    model_timeout              INT UNSIGNED        NOT NULL DEFAULT 300 COMMENT 'LLM请求超时时间，单位为秒',

    -- 智能体配置快照
    agent_use_vision           TINYINT(1) UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用视觉能力：1-是, 0-否',
    agent_max_actions_per_step INT UNSIGNED        NOT NULL DEFAULT 10 COMMENT '单步最大操作数限制',
    agent_max_failures         INT UNSIGNED        NOT NULL DEFAULT 5 COMMENT '最大连续失败次数',
    agent_step_timeout         INT UNSIGNED        NOT NULL DEFAULT 180 COMMENT '单步执行超时时间，单位为秒',
    agent_use_thinking         TINYINT(1) UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否启用思考模式：1-是, 0-否',
    agent_fast_mode            TINYINT(1) UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否启用快速模式：1-是, 0-否',

    -- 浏览器配置快照
    browser_headless           TINYINT(1) UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用无头模式：1-是, 0-否',
    browser_enable_security    TINYINT(1) UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用浏览器安全功能：1-是, 0-否',
    browser_use_sandbox        TINYINT(1) UNSIGNED NOT NULL DEFAULT 1 COMMENT '是否启用浏览器沙箱模式：1-是, 0-否',

    -- 执行结果
    execution_status           VARCHAR(50)         NOT NULL DEFAULT '' COMMENT '执行状态',
    execution_result           TEXT                         DEFAULT NULL COMMENT '执行结果数据',
    execution_faulty           TEXT                         DEFAULT NULL COMMENT '执行错误信息',

    -- 执行耗时（单位：毫秒，便于精确计算）
    execution_duration_ms      INT UNSIGNED        NOT NULL DEFAULT 0 COMMENT '执行耗时，单位为毫秒',
    execution_complete_at      TIMESTAMP                    DEFAULT NULL COMMENT '任务完成时间',

    -- 链式任务信息
    is_chained                 TINYINT(1) UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否为链式任务',
    chain_session_id           VARCHAR(255)        NOT NULL DEFAULT '' COMMENT '链式任务会话ID',
    chain_step_index           INT UNSIGNED        NOT NULL DEFAULT 0 COMMENT '链式任务步骤索引',
    chain_step_total           INT UNSIGNED        NOT NULL DEFAULT 1 COMMENT '链式任务总步骤数',

    -- 审计字段
    created_at                 TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    created_by                 VARCHAR(255)        NOT NULL DEFAULT '' COMMENT '创建者标识'
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  auto_increment = 10000000 COMMENT ='任务执行历史记录表';

-- -----------------------------------------------------------------------------
-- 索引：llm_browser_agent_task_history
-- -----------------------------------------------------------------------------
CREATE INDEX idx_task_history_task_id ON llm_browser_agent_task_history (task_id);
CREATE INDEX idx_task_history_customer_id ON llm_browser_agent_task_history (customer_id);
CREATE INDEX idx_task_history_created_at ON llm_browser_agent_task_history (created_at);
CREATE INDEX idx_task_history_chain_session ON llm_browser_agent_task_history (chain_session_id);
CREATE INDEX idx_task_history_status ON llm_browser_agent_task_history (execution_status);
