# Deviation Protocol：AI 无限流文字游戏后端

第一阶段基础架构：本地行动闸门、确定性规则结算、剧情事实边界、MySQL 事件/快照持久化、异步 Unit of Work，以及最小 FastAPI 健康检查。本阶段不连接任何真实大模型，也不包含完整副本。

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
- `AuthoritativeActionContextFactory` 从 `GameState`、`ContentCatalog` 和不可变的 `AuthoritativeStateView` 自动构造投影，并可签发绑定当前 state/catalog 的 `TrustedResolutionContext`。物品与装备始终使用运行时 instance ID，技能使用 definition ID，NPC 使用会话内 runtime ID；静态 definition ID、展示名称和玩家文本都不是运行时权威标识。
- `ActionGateway` 只负责输入契约、引用权限、玩家/NPC 边界、明显不可行输入和本地/叙事路由；`DeterministicRuleResolver` 不接受调用方传入 route，而是从可信上下文内部强制运行 gateway 后执行查询或规则结算。两者都不生成文学叙事。
- 状态、库存、装备、技能、资源、货币和任务占位查询完全在本地完成。装备、卸下、显式标记为 `consumable` 的物品使用、经权威机会授权的技能学习、技能升级和结构化技能使用也在本地结算。
- `TALK`、`CHOOSE`、`CUSTOM`、`EXPLORE`、`OBSERVE` 和 `MOVE` 等合法开放行动返回 `NARRATIVE_REQUIRED`；解析器只传递已验证意图和权威事实，不预写永久状态，也不把普通创意行动提升为异常。
- 玩家输入没有 grant item/skill、增加货币/资源、改属性、改 NPC、伪造 gateway/fact 或生成装备实例的字段。系统奖励只能由经过授权的规则或剧情事件调用领域能力；技能学习要求来自持久化事实、奖励结算或系统规则的密封授权能力，普通 `ActionContext` 不能携带该授权。
- `DeterministicEffectExecutor` 当前仅执行 catalog 中经过验证且未被改写的 `ATTRIBUTE_MODIFIER` 和 `RESOURCE_MODIFIER`。属性修改只支持显式系统规则/奖励产生的永久变化；技能和装备不能把临时加成写入基础属性。未知、被改写、语义不支持或其他效果类型会明确失败，不会静默忽略，也不会执行脚本或表达式。
- 多效果、技能成本和物品变化都先应用到 `GameState` 快照副本；全部验证成功才返回候选新状态，任一失败则不返回状态或成功事件，原聚合完全不变。
- `ResolutionResult` 将待持久化的 `DomainEventDraft`、带 kind 的 `NarrativeFact` 和安全的 `PlayerFeedback` 分开，对跨字段状态和深度不可变 JSON 值进行校验。事件 ID、数据库序号和时间戳由事务编排器封装成 `DomainEvent`，不在纯规则结算中生成。
- `action_signature` 是规范化语义负载的 SHA-256；忽略重试用的 `client_request_id`，但覆盖其余所有玩家字段。目标/工具按集合语义排序去重，文本统一 NFC 和空白但保留大小写。
- `turn_requests(session_id, client_request_id)` 唯一约束是最终幂等防线；回合骨架先锁定会话行，再返回已保存响应，避免并发重试触发第二次业务处理。
- 快照保留频繁变化的游戏状态 JSON，避免第一阶段过早拆列；关键查询字段、事件和幂等记录保持关系化。
- Repository 以 `WHERE state_version = expected` 更新会话。更新、快照和事件共享同一个 `AsyncSession`，由 Unit of Work 原子提交。
- 异常候选路由和独立 `AnomalyEvaluator` 端口已经预留，但第一阶段不做主观异常判断。
- `RuleResolver` 不写数据库、不提交 Unit of Work、不处理 `client_request_id` 幂等，也不负责最终文学输出。异常评估算法仍未实现。

更多责任边界见 [`docs/architecture.md`](docs/architecture.md)。

Phase 1.1 的演示内容包位于 `config/demo_content_pack.json`。它只用于验证角色、NPC、装备、消耗品、技能和结构化效果的加载，不包含正式剧情。静态内容由基础设施层加载后交给纯领域 `ContentCatalog` 验证；运行时 `GameState` 则以带版本的 JSON 形状继续保存到现有快照中。
