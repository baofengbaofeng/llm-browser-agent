# LLM Browser Agent

> A Tornado-based asynchronous web service that uses an LLM to plan and execute browser automation tasks.

本项目提供一个“自然语言 → 结构化步骤 → 浏览器执行”的端到端能力，支持前端页面配置、任务提交、实时执行日志与历史记录查询。

---

## Overview

LLM Browser Agent is an **async** web application built on Tornado. It combines:

- **LLM planning**: Convert user instructions into a plan (text or JSON actions).
- **Browser automation**: Execute steps via `browser-use`.
- **Realtime events**: Task logs/status via in-process event delivery (SSE interface reserved).
- **I18n**: UI translations via TOML assets.
- **Async persistence**: Tortoise ORM + SQLite by default (can be extended).

---

## Features

- **Natural language tasks**: Submit one-step or chained multi-step prompts.
- **Configurable runtime**: Model / agent / browser settings via TOML + per-customer overrides.
- **Task history**: Create and query task history and task projects.
- **Security headers**: CSP and common security headers via `secure` and Tornado hooks.

---

## Tech Stack

| Layer | Choice |
|------|--------|
| Web | Tornado |
| ORM | Tortoise ORM |
| DB | SQLite (default) |
| LLM client | `langchain_openai` (`ChatOpenAI`) |
| Browser automation | `browser-use` |
| Config | TOML |
| Frontend | HTML template + vanilla JS |

---

## Architecture

- **Web layer**: `src/web/` (entrypoint, routing, handlers, templates, static assets)
- **Application layer**: `src/apps/` (executor, task/history/project, i18n, instruct parsing)
- **Core infra**: `src/core/` (database, security, validators)
- **Models**: `src/models/` (Tortoise models)
- **Environment**: `src/environment/` (TOML config assets + typed accessors)

---

## Quick Start

### Prerequisites

- **Python**: 3.11+ (recommended 3.12)
- **Browser**: Chrome/Chromium available in runtime environment

### Install Dependencies

This repo currently does not ship a lockfile (`requirements.txt`/`pyproject.toml`). Install dependencies based on imports:

```bash
pip install tornado tortoise-orm sqlglot toml bleach secure nest_asyncio pydantic pytest
pip install langchain-openai browser-use
```

### Run (Development)

The service uses `src/` layout. Make sure `src` is on `PYTHONPATH`.

```bash
export PYTHONPATH=src
python -m web.main
```

Then open `http://localhost:8080`.

> Alternative: `PYTHONPATH=src python src/web/main.py`

---

## Configuration

### Config Files

Default config lives at:

- `src/environment/assets/environment.toml`
- Optional environment override via CLI: `--env=<name>`
  - File path: `src/environment/assets/environment-<name>.toml`

Example:

```bash
export PYTHONPATH=src
python -m web.main --env=test
```

### Key Config Options (TOML)

- **Server**
  - `llm_browser_agent.server.port`
  - `llm_browser_agent.server.debug`
  - `llm_browser_agent.server.shutdown_timeout`
- **Database**
  - `llm_browser_agent.server.database.url` (SQLite by default)
- **Model**
  - `llm_browser_agent.model.name`
  - `llm_browser_agent.model.api_url`
  - `llm_browser_agent.model.api_key`
  - `llm_browser_agent.model.timeout`
- **Agent / Browser**
  - `llm_browser_agent.agent.*`
  - `llm_browser_agent.browser.*`

> Security note: do **NOT** commit real secrets (API keys / cookie secrets) into VCS in production usage.

---

## Database

Default DB URL in `environment.toml` is SQLite:

```toml
llm_browser_agent.server.database.url = "sqlite://.data/llm_browser_agent.db"
```

On startup, the app will initialize the SQLite file (if missing) and execute DDL from:

- `deployments/ddl/database.sql`

---

## HTTP API

Routes are registered in `src/web/main.py`.

### Task

| Path | Method | Description |
|------|--------|-------------|
| `/api/task/` | POST | Submit a task (single or chained prompts) |
| `/api/task/{task_id}/status/` | GET | Get task status |
| `/api/task/{task_id}/cancel/` | POST | Cancel a task |
| `/api/task/{task_id}/stream/` | GET | Task stream endpoint (reserved) |

### Configuration

| Path | Method | Description |
|------|--------|-------------|
| `/api/configuration/` | GET | All config |
| `/api/configuration/model/` | GET | Model config |
| `/api/configuration/agent/` | GET | Agent config |
| `/api/configuration/browser/` | GET | Browser config |

### Customer / Plans / History

| Path | Method | Description |
|------|--------|-------------|
| `/api/customer/task/args/` | GET | Get customer task args (custom or default) |
| `/api/customer/task/plan/` | GET/POST/DELETE | Task project CRUD |
| `/api/task/history/` | GET | History list (pagination) |
| `/api/task/history/{id}/` | GET | History detail |
| `/api/task/history/task/{task_id}/` | GET | History by task id |
| `/api/task/history/chain/{session_id}/` | GET | History by chained session |

### Instruct / Language / UI

| Path | Method | Description |
|------|--------|-------------|
| `/api/task/instruct/` | POST | Parse instruction into plan/actions |
| `/api/language/` | GET | Translation mapping |
| `/` | GET | UI index page |

---

## Project Structure

```
src/
  web/
    __init__.py
    main.py              # HTTP entrypoint (Tornado app + routing + lifecycle)
    templates/           # HTML templates
    static/              # Static assets (css/js/images)
    handlers/            # Tornado HTTP handlers
      assets/            # i18n error message assets for handlers
  apps/                  # Application layer (executor, task, language, instruct)
  core/                  # Infra (database, security, validators)
    security/            # Security headers and sanitization
    database/
  environment/           # TOML config assets and accessors
  models/                # Tortoise ORM models
  tests/                 # Unit tests
```

---

## Testing

```bash
export PYTHONPATH=src
pytest -q
```

---

## Troubleshooting

### ImportError: cannot import module under src/

Make sure `src` is on `PYTHONPATH`:

```bash
export PYTHONPATH=src
python -m web.main
```

### TOML parse error

Check TOML assets under `src/environment/assets/` and `src/apps/**/assets/` for valid TOML syntax.

---

## License

Apache 2.0 License
