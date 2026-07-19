# Deviation Protocol：AI 无限流文字游戏后端

第一阶段基础架构：本地行动闸门、剧情事实边界、MySQL 事件/快照持久化、异步 Unit of Work，以及最小 FastAPI 健康检查。本阶段不连接任何真实大模型，也不包含完整副本。

## 结构

```text
src/deviation_protocol/
  domain/            # 纯领域模型、行动策略、剧情事实、领域事件
  application/       # ActionGateway、回合骨架与所有应用端口
  infrastructure/    # MySQL/SQLAlchemy Repository 与 Unit of Work
  api/               # 最小 FastAPI 应用
config/              # 策略顺序、开关、正则与本地行动配置
alembic/              # MySQL 迁移
tests/unit/           # 不依赖数据库的规则与事务边界测试
tests/integration/    # 仅使用显式 TEST_DATABASE_URL 的 MySQL 测试
docs/                 # 架构说明
```

依赖方向为 `api/infrastructure -> application -> domain`。领域层不导入 FastAPI、SQLAlchemy 或任何模型供应商 SDK。

## 运行环境与依赖

项目目标为 Python 3.12，依赖通过 `pyproject.toml` 管理：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

数据库驱动选择 `asyncmy`，原因是项目从空仓库创建，适合直接使用 SQLAlchemy 2.x `AsyncSession`；它是原生 asyncio MySQL 驱动，避免在线程池中包装同步连接。系统只接受 `mysql+asyncmy://` URL，不支持也不会回退到 SQLite。

## 配置 MySQL 8

先以数据库管理员身份创建数据库和最小权限账号（账号名和密码仅为示例，请自行替换）：

```sql
CREATE DATABASE deviation_protocol
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'game_user'@'%' IDENTIFIED BY 'replace-with-a-secret';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP, REFERENCES
  ON deviation_protocol.* TO 'game_user'@'%';
```

复制 `.env.example` 为本地 `.env`，再填写真实连接信息。不要提交 `.env`：

```dotenv
DATABASE_URL=mysql+asyncmy://game_user:replace-with-a-secret@127.0.0.1:3306/deviation_protocol?charset=utf8mb4
```

连接建立后会执行 `SET time_zone = '+00:00'`；应用生成的时间同样使用 UTC。MySQL `DATETIME` 本身不携带时区，读写约定始终是 UTC。

## 迁移

在线升级需要 `DATABASE_URL`，Alembic 不会在导入应用或运行普通单元测试时自动连接数据库：

```powershell
$env:DATABASE_URL = "mysql+asyncmy://game_user:secret@127.0.0.1:3306/deviation_protocol?charset=utf8mb4"
alembic upgrade head
```

没有数据库时仍可离线检查首份迁移生成的 MySQL SQL：

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
alembic upgrade head --sql
```

迁移创建的所有业务表均显式使用 InnoDB/utf8mb4，结构化状态和事件负载使用 MySQL 原生 JSON。Alembic 自身的版本表继承数据库默认引擎与字符集。

## 测试与启动

```powershell
pytest
python -m compileall -q src tests alembic
uvicorn deviation_protocol.api.main:app --app-dir src --reload
```

健康检查为 `GET /health`，它只证明进程可服务，不会隐式打开数据库连接。

MySQL 集成测试仅在显式设置 `TEST_DATABASE_URL` 后运行：

```powershell
$env:TEST_DATABASE_URL = "mysql+asyncmy://game_test_user:secret@127.0.0.1:3306/deviation_protocol_test?charset=utf8mb4"
pytest -m integration
```

未设置时测试会明确显示 `skip`。测试套件绝不会创建 SQLite 数据库或把 SQLite 当作替代品。

## 核心设计

- `ActionSubmission` 表达单一主要意图；Pydantic 负责长度和基本形状，跨字段约束由策略记录进 trace。
- `ActionGateway` 按 `config/action_policies.json` 的顺序和开关装配小型策略类。拒绝、本地解析和正常叙事是确定性路由。
- `action_signature` 是规范化语义负载的 SHA-256；忽略重试用的 `client_request_id`，但包含会话与回合。
- `turn_requests(session_id, client_request_id)` 唯一约束是最终幂等防线；回合骨架先锁定会话行，再返回已保存响应，避免并发重试触发第二次业务处理。
- 快照保留频繁变化的游戏状态 JSON，避免第一阶段过早拆列；关键查询字段、事件和幂等记录保持关系化。
- Repository 以 `WHERE state_version = expected` 更新会话。更新、快照和事件共享同一个 `AsyncSession`，由 Unit of Work 原子提交。
- 异常候选路由和独立 `AnomalyEvaluator` 端口已经预留，但第一阶段不做主观异常判断。

更多责任边界见 [`docs/architecture.md`](docs/architecture.md)。

Phase 1.1 的演示内容包位于 `config/demo_content_pack.json`。它只用于验证角色、NPC、装备、消耗品、技能和结构化效果的加载，不包含正式剧情。静态内容由基础设施层加载后交给纯领域 `ContentCatalog` 验证；运行时 `GameState` 则以带版本的 JSON 形状继续保存到现有快照中。
