from tortoise import BaseDBAsyncClient  # Tortoise migration DB client type hint for async upgrade and downgrade scripts

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "llm_browser_agent_task_project" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            "customer_id" VARCHAR(255) NOT NULL,
            "task_prompt" TEXT NOT NULL,
            "task_digest" VARCHAR(100) NOT NULL,
            "model_name" VARCHAR(100) NOT NULL,
            "model_temperature" VARCHAR(40) NOT NULL,
            "model_top_p" VARCHAR(40) NOT NULL,
            "model_api_url" VARCHAR(255) NOT NULL,
            "model_api_key" VARCHAR(255) NOT NULL,
            "model_timeout" INT NOT NULL,
            "agent_use_vision" INT NOT NULL,
            "agent_max_actions_per_step" INT NOT NULL,
            "agent_max_failures" INT NOT NULL,
            "agent_step_timeout" INT NOT NULL,
            "agent_use_thinking" INT NOT NULL,
            "agent_calculate_cost" INT NOT NULL,
            "agent_fast_mode" INT NOT NULL,
            "agent_demo_mode" INT NOT NULL,
            "browser_headless" INT NOT NULL,
            "browser_enable_security" INT NOT NULL,
            "browser_use_sandbox" INT NOT NULL,
            "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "created_by" VARCHAR(255) NOT NULL,
            "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_by" VARCHAR(255) NOT NULL
        ) /* Task project entity table storing task plan configuration. */;

        CREATE TABLE IF NOT EXISTS "llm_browser_agent_customer_profile" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            "customer_id" VARCHAR(255) NOT NULL UNIQUE,
            "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "created_by" VARCHAR(255) NOT NULL,
            "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_by" VARCHAR(255) NOT NULL
        ) /* Customer profile entity table storing customer identifiers and audit information. */;

        CREATE TABLE IF NOT EXISTS "llm_browser_agent_customer_setting" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            "customer_id" VARCHAR(255) NOT NULL,
            "snapshot_id" INT NOT NULL,
            "model_name" VARCHAR(100) NOT NULL,
            "model_temperature" VARCHAR(40) NOT NULL,
            "model_top_p" VARCHAR(40) NOT NULL,
            "model_api_url" VARCHAR(255) NOT NULL,
            "model_api_key" VARCHAR(255) NOT NULL,
            "model_timeout" INT NOT NULL,
            "agent_use_vision" INT NOT NULL,
            "agent_max_actions_per_step" INT NOT NULL,
            "agent_max_failures" INT NOT NULL,
            "agent_step_timeout" INT NOT NULL,
            "agent_use_thinking" INT NOT NULL,
            "agent_calculate_cost" INT NOT NULL,
            "agent_fast_mode" INT NOT NULL,
            "agent_demo_mode" INT NOT NULL,
            "browser_headless" INT NOT NULL,
            "browser_enable_security" INT NOT NULL,
            "browser_use_sandbox" INT NOT NULL,
            "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "created_by" VARCHAR(255) NOT NULL
        , UNIQUE("customer_id", "snapshot_id")
        ) /* Customer setting entity table storing versioned history of customer configuration snapshots. */;

        CREATE TABLE IF NOT EXISTS "llm_browser_agent_task_history" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            "customer_id" VARCHAR(255) NOT NULL,
            "task_id" VARCHAR(255) NOT NULL,
            "task_prompt" TEXT NOT NULL,
            "model_name" VARCHAR(100) NOT NULL,
            "model_temperature" VARCHAR(40) NOT NULL,
            "model_top_p" VARCHAR(40) NOT NULL,
            "model_api_url" VARCHAR(255) NOT NULL,
            "model_timeout" INT NOT NULL,
            "agent_use_vision" INT NOT NULL,
            "agent_max_actions_per_step" INT NOT NULL,
            "agent_max_failures" INT NOT NULL,
            "agent_step_timeout" INT NOT NULL,
            "agent_use_thinking" INT NOT NULL,
            "agent_fast_mode" INT NOT NULL,
            "browser_headless" INT NOT NULL,
            "browser_enable_security" INT NOT NULL,
            "browser_use_sandbox" INT NOT NULL,
            "execution_status" VARCHAR(50) NOT NULL,
            "execution_result" TEXT,
            "execution_faulty" TEXT,
            "execution_duration_ms" INT NOT NULL DEFAULT 0,
            "execution_complete_at" TIMESTAMP,
            "is_chained" INT NOT NULL DEFAULT 0,
            "chain_session_id" VARCHAR(255) NOT NULL,
            "chain_step_index" INT NOT NULL DEFAULT 0,
            "chain_step_total" INT NOT NULL DEFAULT 1,
            "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "created_by" VARCHAR(255) NOT NULL,
            "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_by" VARCHAR(255) NOT NULL
        ) /* Task execution history entity table storing submission parameters, results, and duration. */;

        CREATE TABLE IF NOT EXISTS "aerich" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            "version" VARCHAR(255) NOT NULL,
            "app" VARCHAR(100) NOT NULL,
            "content" JSON NOT NULL
        );"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
)

