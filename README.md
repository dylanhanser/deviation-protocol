# Deviation Protocol：AI 无限流文字游戏后端

当前实现到 Phase 2.2c：生产 action API 已接入耐久的 prepare / provider / finalize 三阶段协调器。外部 DeepSeek 调用发生在所有 UoW、`AsyncSession` 与 MySQL 行锁退出之后；模型只选择本回合 opaque outcome token，最终状态仍由服务器声明式规则、`NarrativeOutcomePolicy`、专用 issuer 与 `StoryDirector` 决定。

## Phase 2.2c production narrative coordination

`narrative_jobs` is created by the independent `20260719_0003` migration with InnoDB/utf8mb4, MySQL JSON, session/client-request uniqueness, cascading session deletion, and session/status plus status/lease indexes. Its normal lifecycle is `PREPARED -> IN_PROGRESS -> PROPOSAL_VALIDATED -> COMMITTED`; safe terminal states include `FAILED_RETRYABLE`, `FAILED_TERMINAL`, `STALE`, and `OUTCOME_UNKNOWN`. Jobs persist only the bounded player-safe request, request/state fingerprints, scenario version, provider/model names, lease metadata, a validated-but-unaccepted proposal subset, stable error codes, and—only for COMMITTED jobs—accepted text. The proposal subset includes candidate prose for crash recovery. It is internal, non-authoritative, and never a player response or recent-context source. Terminal jobs may retain it until their job/session row is deleted. Jobs never persist credentials, Authorization headers, the full system prompt, raw provider envelopes, or chain-of-thought.

The transaction boundaries are strict: Phase A locks the session, checks idempotency and authoritative catalogs/state/gateway/rules, computes a safe frame/request, persists PREPARED, commits, and exits the UoW. Phase B claims the job in a short transaction and exits every database context before calling the provider; validation is persisted immediately in another short transaction. Phase C locks session then job, rechecks version/fingerprint/action/scenario/lease, recomputes outcome tokens, and invokes the policy/issuer/StoryDirector chain. Accepted narrative text, snapshot, events, turn response, COMMITTED job, and session version commit atomically. Rejection, stale/CAS failure, or database failure never exposes the internally retained candidate prose.

The model sees opaque per-turn outcome tokens and safe descriptions, never internal rule IDs or effect templates. `NarrativeOutcomePolicy` recomputes eligibility against locked authority; `NarrativeEventIssuer` can emit `VALIDATED_NARRATIVE_OUTCOME` only from server-defined templates. The opening content has only three minimal data-driven permissions: purposeful life signalling (success/ambiguous/failure), quiet observation (no NPC life confirmation), and constrained custom no-effect. Player text ordering a nurse to acknowledge life cannot select success. Prose consistency is a conservative structural and data-defined term check, not a general semantic verifier; prose and dialogue never establish facts, and only the sealed server event is authoritative.

An active duplicate returns HTTP 202 without another provider call; another same-session mutation returns stable 409 while local read-only queries remain available. An expired PROPOSAL_VALIDATED job receives a new finalize-only fenced lease and resumes without invoking the provider. An expired IN_PROGRESS job becomes `OUTCOME_UNKNOWN`: the database cannot distinguish a crash before send from a sent request whose result or charge was lost, so it is never automatically resent. Job-level provider invocation is capped at one. DeepSeek defaults to zero transport retries (one HTTP attempt); an operator may explicitly opt into at most two retries (three attempts total), which can duplicate provider work or billing after an ambiguous timeout or disconnect. Exactly-once provider billing is not guaranteed by this system. A future worker may reuse the job ports, but Phase 2.2c contains no worker, queue, or distributed task system. `DeviationEvaluator`, anomaly effects, combat, and the frontend remain unimplemented.

## 结构

```text
src/deviation_protocol/
  domain/            # 纯领域模型、行动策略、剧情事实、领域事件
  application/       # ActionGateway、TurnOrchestrator、响应模型与应用端口
  infrastructure/    # MySQL/SQLAlchemy Repository 与 Unit of Work
  api/               # 最小 FastAPI 应用
config/              # 策略顺序、开关、正则与本地行动配置
alembic/              # MySQL 迁移
tests/unit/           # 不依赖数据库的规则与事务边界测试
tests/integration/    # 仅使用显式 TEST_DATABASE_URL 的 MySQL 测试
docs/                 # 架构说明
```

依赖方向为 `api/infrastructure -> application -> domain`。领域层不导入 FastAPI、SQLAlchemy 或任何模型供应商 SDK。

## Windows 开发环境与验证

Windows 开发需要 PowerShell 7+（`pwsh`）。仓库 `.venv` 中的 Python 3.12.x 是唯一项目解释器；项目命令始终显式使用 `.\.venv\Scripts\python.exe`，不要改用系统或全局 Python。

只读诊断会检查 PowerShell、项目解释器、pytest、Git、安全的工作树摘要、环境变量是否存在，以及离线 Alembic heads/history。它不读取 `.env`，不连接 MySQL，也不调用 DeepSeek：

```powershell
.\scripts\doctor.ps1
.\scripts\doctor.ps1 -Strict
```

统一验证脚本提供四种模式：

```powershell
.\scripts\verify.ps1 -Mode Quick
.\scripts\verify.ps1 -Mode Full
.\scripts\verify.ps1 -Mode MySQL
.\scripts\verify.ps1 -Mode Security
```

- `Quick`：编译检查、单元测试和 `git diff --check`。
- `Full`：完整 pytest、编译检查、依赖一致性、离线 Alembic 元数据和 Git 差异检查；没有测试数据库变量时保留集成测试原有的 skip 行为。
- `MySQL`：只有 `TEST_DATABASE_URL` 经安全解析为 `mysql+asyncmy` 且数据库名严格为 `deviation_protocol_test` 时才运行集成测试；不会借用 `DATABASE_URL`，也不会运行不具备该安全入口的在线 Alembic 命令。
- `Security`：运行现有单元测试中的架构、配置、SQLite fallback、Provider 和敏感信息边界，并检查 Git 差异；不连接 MySQL 或 DeepSeek。

live DeepSeek 测试默认关闭，必须由用户在独立命令中显式 opt-in。只要 `RUN_LIVE_DEEPSEEK_TEST` 为真值，以上四种普通验证都会在 pytest 启动前拒绝执行，避免意外网络请求和 Token 消耗。

本地只读副本内容检查可使用 Scenario Workbench：

```powershell
.\.venv\Scripts\python.exe -m deviation_protocol.tools.scenario validate config/scenarios/death_certificate_v1.json
```

它提供 `validate`、`analyze`、`preview` 和稳定 `--json` 输出，不连接数据库或调用模型。完整用法与静态分析边界见 [`docs/scenario_workbench.md`](docs/scenario_workbench.md)。

隔离草案可用 `scenario new --scenario-id <id> --title <title> --premise <note> --output-dir .\scenario-drafts` 创建；Windows 上它以全新目录发布且从不覆盖现有内容。缺少标准库原子 no-replace 目录发布语义的平台会拒绝实际写入，而不是降级为可能覆盖空目录的 rename。

### Engineering guidance

Before changing persistence, trusted authority, narrative orchestration, scenario tooling, or verification workflows, read:

- [Engineering guardrails](docs/engineering/guardrails.md)
- [Codex workflow](docs/engineering/codex_workflow.md)

The guardrails document records reusable rules derived from confirmed failures. The workflow document defines implementation, independent review, environment, verification, and Git handoff procedures.

## 运行环境与依赖

项目目标为 Python 3.12，依赖通过 `pyproject.toml` 管理：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
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
.\.venv\Scripts\python.exe -m alembic upgrade head
```

没有数据库时仍可离线检查首份迁移生成的 MySQL SQL：

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m alembic upgrade head --sql
```

迁移创建的所有业务表均显式使用 InnoDB/utf8mb4，结构化状态和事件负载使用 MySQL 原生 JSON。Alembic 自身的版本表继承数据库默认引擎与字符集。

## 测试与启动

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m compileall -q src tests alembic
.\.venv\Scripts\python.exe -m uvicorn deviation_protocol.api.main:app --app-dir src --reload
```

健康检查为 `GET /health`，它只证明进程可服务，不会隐式打开数据库连接。

MySQL 集成测试仅在显式设置 `TEST_DATABASE_URL` 后运行：

```powershell
$env:TEST_DATABASE_URL = "mysql+asyncmy://game_test_user:secret@127.0.0.1:3306/deviation_protocol_test?charset=utf8mb4"
.\.venv\Scripts\python.exe -m pytest -m integration
```

未设置时测试会明确显示 `skip`。测试套件绝不会创建 SQLite 数据库或把 SQLite 当作替代品。

## 核心设计

Phase 1.3 已将确定性组件接入真实事务编排：`FirstPhaseTurnOrchestrator` 先以 `SELECT ... FOR UPDATE` 锁定会话，再按 `(session_id, client_request_id)` 查询已保存响应；新请求加载会话与最新快照，严格核对数据库状态版本、快照 `schema_version` 和 `content_version`，使用构造注入的 `ContentCatalog` 完整反序列化 `GameState`。快照缺失、损坏或版本不兼容都会以明确应用错误停止，不会创建或保存默认空状态。application 层不读取内容 JSON 文件。

状态加载成功后，编排器才通过 `AuthoritativeActionContextFactory.create_trusted` 为当前状态签发新的 `TrustedResolutionContext`。当前没有持久化场景可见性、奖励或剧情事实来源，因此默认可见/可交互 NPC、环境工具和技能学习授权均为空。请求模型禁止玩家传入 catalog、gateway route/decision、叙事事实、授权能力或 context digest。

`ResolutionResult` 的四种持久化规则如下：

- `REJECTED_LOCAL`：保存可幂等返回的结构化响应，不写候选快照、不写成功事件，`state_version` 不变。
- `RESOLVED_LOCAL` 查询：保存查询响应，不调用 `NarrativeProvider`，不写快照或事件，`state_version` 不变。
- `RESOLVED_LOCAL` 状态突变：再次验证候选状态，将 `state_version` 恰好增加一次，按 draft 顺序封装全部事件，并在同一 UoW 内原子保存快照、事件、会话版本与 turn response。
- `NARRATIVE_REQUIRED`：保存 `required/pending` 响应，不提前修改永久状态、不写成功事件，`state_version` 不变；本阶段不调用真实 `NarrativeProvider`。

严格 `TurnResponse` 只包含会话/请求标识、`action_signature`、resolution/result/feedback、安全 JSON 参数、结果状态版本、叙事标记和必要的本地查询结果。已存 JSON 必须重新通过同一模型验证后才能返回；响应不包含 `GameState`、可信上下文、授权能力或数据库异常文本。

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
- `turn_requests(session_id, client_request_id)` 唯一约束是最终幂等防线；编排器先锁定会话行，再交叉校验已存 `turn_id`、`action_signature` 和响应绑定。同一动作重放旧响应，不同动作或不同 turn 复用该键会明确抛出 `IdempotencyConflictError`。若唯一约束仍捕获竞态，失败事务回滚后只重读 winner，不再次调用 resolver。`action_signature` 只表达语义等价，不替代 `client_request_id` 幂等键。
- 快照保留频繁变化的游戏状态 JSON，避免第一阶段过早拆列；关键查询字段、事件和幂等记录保持关系化。
- Repository 以 `WHERE state_version = expected` 更新会话，并以同一预期版本条件更新已有快照；任一 `rowcount=0` 或已存快照版本不匹配都抛出 `OptimisticLockError`，不会覆盖较新快照。更新、快照、事件和 turn response 共享同一个 `AsyncSession`，由 Unit of Work 只提交一次；Repository 自身不提交。
- 事件元数据由编排器使用可注入 Clock 和 ID generator 生成。编排器在会话行锁保护下读取当前最大 `sequence_no`，保证同会话连续、稳定并保留 draft 顺序；事件沿用 `(session_id, turn_id)` 与 turn request/response 关联，响应中的 `resulting_state_version` 是该 turn 的状态版本关联。
- 异常候选路由和独立 `AnomalyEvaluator` 端口已经预留，但第一阶段不做主观异常判断。
- `RuleResolver` 不写数据库、不提交 Unit of Work、不处理 `client_request_id` 幂等，也不负责最终文学输出。现行 Phase 2.2c 由编排器在 resolver 之后接入 `NarrativeProvider`；`DeviationEvaluator` 仍未接入，默认流程拒绝 `ANOMALY_EVALUATION_REQUIRED`。

更多责任边界见 [`docs/architecture.md`](docs/architecture.md)。

Phase 1.1 的演示内容包位于 `config/demo_content_pack.json`。它只用于验证角色、NPC、装备、消耗品、技能和结构化效果的加载，不包含正式剧情。静态内容由基础设施层加载后交给纯领域 `ContentCatalog` 验证；运行时 `GameState` 则以带版本的 JSON 形状继续保存到现有快照中。

## Phase 1.4 会话 API

FastAPI 现在通过 app factory 公开版本化会话边界，并保留不连接数据库的健康检查：

```text
GET  /health
POST /v1/sessions
GET  /v1/sessions/{session_id}
GET  /v1/sessions/{session_id}/state
POST /v1/sessions/{session_id}/actions
```

Windows 开发环境按仓库约束启动：

```powershell
$env:DATABASE_URL = "mysql+asyncmy://game_user:secret@127.0.0.1:3306/deviation_protocol?charset=utf8mb4"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn deviation_protocol.api.main:app --app-dir src --reload
```

`create_app()` 在模块导入时不会创建 engine、连接数据库或运行迁移。默认运行依赖在 FastAPI lifespan 启动时装配，并在关闭时释放 engine；测试可以注入完整 `ApiServices`，也可以覆盖 principal dependency。

当前 `get_current_principal` 明确使用固定的 `demo-dev-only` 身份 `demo-player`。它只是尚未接入 JWT/OAuth 时的开发占位，客户端请求正文不能选择 `player_id`。生产部署前必须替换该 dependency。所有会话查询与行动都会用可信 principal 检查 ownership；不存在与无权访问统一返回安全的 `SESSION_NOT_FOUND` 404。

创建请求只接受 `client_request_id` 与 `character_definition_id`。角色必须来自当前 `ContentCatalog`，初始 `GameState`、session 和 version-zero snapshot 在同一 UoW 中提交。数据库唯一约束 `(player_id, creation_client_request_id)` 是并发幂等防线；重放相同创建返回同一 session，不会把 `session_id` 当作客户端幂等键。每个 session 将当前 catalog 版本固定为 `content_version`。

会话元数据接口只返回 phase、版本、时间戳和安全角色概要，不返回快照。`/state` 使用独立的 `PlayerVisibleStateProjection` 新建玩家公开属性、资源、钱包、库存、装备和技能数据；它不会调用 `GameState.model_dump()` 作为响应。当前尚无可信场景可见性来源，因此 `visible_npcs` 默认为空，而不是暴露快照中的全部 NPC；任务状态目前也是安全空占位。

行动请求正文不含 `session_id` 或 `player_id`，并拒绝 outcome token、job/lease、Provider、proposal、可信事件和其他未知字段。endpoint 在 ownership 检查后调用 `DurableNarrativeTurnOrchestrator`。公共响应不暴露 `action_signature`、内部 token 绑定、job/lease、raw proposal、prompt 或 Provider 配置；pending 返回 202，成功或幂等重放返回 200。本地 query/reject/mechanical/确定性 CHOOSE 与终局不调用 Provider。当前仍没有战斗、`DeviationEvaluator`、异常效果或前端。

API 错误统一为：

```json
{
  "error": {
    "error_code": "STABLE_ERROR_CODE",
    "message": "Safe public message"
  }
}
```

请求校验为 422，ownership/not-found 为 404，幂等与乐观锁冲突为 409，内容或快照不兼容为 409，未预期异常为不含 SQL、路径或堆栈的 500。

## Phase 2.1 数据驱动剧情运行时

Phase 2.1 新增与具体题材无关的 `ScenarioDefinition`、`ScenarioRuntimeState`、`DecisionCadencePolicy`、`NarrativeFrame` 和 `DeterministicStoryDirector`。引擎只解释经过白名单验证的 Scenario、Phase、Fact、Clue、ThreatClock、DecisionWindow 与 Transition；不按副本、阶段、NPC 或线索 ID 写分支，也不支持 `eval`、脚本表达式或动态导入。JSON 读取由 `infrastructure.scenario_loader` 负责，领域模型负责严格字段、版本、引用、可达性、出口、线索阈值、职业替代路径、时钟边界和有界自动循环校验。

静态 `ScenarioDefinition` 保存内容与规则；快照中的 `ScenarioRuntimeState` 只保存剧情推进状态。NPC 关系、背包、技能、钱包和资源继续由原有权威状态保存，不在副本运行时重复。快照 schema 已显式升级到 v2，并提供无副作用的 v1→v2 迁移；副本 `content_version` 与快照 `schema_version` 是互相独立的兼容轴，MySQL 仍使用现有 JSON 字段。

`DeterministicStoryDirector` 只接收定义、状态、职业标签和经服务器内部边界密封的结构化事件；普通可反序列化 `VerifiedScenarioEvent` 只有数据形状，没有推进剧情的权限，密封后再改写负载同样会失效。Director 先在深拷贝候选上应用事实、线索、时钟、转场与结局，再输出候选状态和严格 `NarrativeFrame`。它不读取系统时间、不使用随机数或 UUID、不访问数据库、不调用模型，也不生成文学文本。`NarrativeFrame` 只含玩家当前可知事实；可见 NPC 必须同时存在于 `GameState.npcs` 并被当前位置引用，NPC 分区只携带该 NPC 权限范围与玩家当前知识的安全交集。建议动作由代码从内容包生成。未来可替换的 `NarrativeProvider` 只能渲染该框架，不能修改固定事实、时钟或权威状态。

决策窗口由独立策略控制。开局可声明一次立即生存决策，前期以较大的 beat 间隔保持低频，调查阶段只在声明的关键窗口停下，核心冲突可进入 rapid 模式缩短间隔。普通移动、开门、读取必要信息或本地查询不会自行制造决策；本地查询也不推进 beat 或时钟。每帧的数据结构最多容纳一个决策，阶段最大自动 beat 和严格失败路径共同防止无限自动推进或永不决策。

首个正式结构化内容包位于 `config/scenarios/death_certificate_v1.json`，规格见 `docs/scenarios/death_certificate_v1.md`。仓库只包含原创的结构化设计，没有参考小说原文或改写文本。Phase 2.2c 只为现有开局增加三类最小声明式 outcome 规则，没有扩写完整后续剧情。

## Phase 2.2a 场景事务接线

`POST /v1/sessions` 现在必须由玩家显式提交服务器允许的 `scenario_id`，同时继续提交经 `ContentCatalog` 验证的 `character_definition_id`。玩家不能提交 scenario 内容版本、初始 phase、事实、线索、时钟、`ScenarioRuntimeState`、`NarrativeFrame` 或可信事件。lifespan 加载 `ScenarioCatalog` 及其匹配的 `ContentCatalog`；`SessionService` 创建基础 `GameState` 和场景引用的运行时 NPC，再调用纯 `DeterministicStoryDirector.start_scenario()`。得到的 v2 快照、session 行与创建幂等绑定在同一个 UoW 中一次提交，响应只附带安全初始 `NarrativeFrame`。同一玩家的创建键同时绑定角色与 scenario；任一项不同均为 409，不同玩家仍可复用同一键。

实际创建流为：

```text
principal + creation key + character_definition_id + scenario_id
  -> ContentCatalog / ScenarioCatalog 校验
  -> GameState + runtime NPCs
  -> StoryDirector.start_scenario
  -> ScenarioRuntimeState + safe NarrativeFrame
  -> game_sessions + v2 game_snapshots（同一事务）
```

行动仍先锁定 session 行并检查 `(session_id, client_request_id)` 幂等记录，然后加载版本一致的 v2 `GameState` 与匹配的两个目录。`ActionGateway` 和 `DeterministicRuleResolver` 永远先运行；Director 不访问 Repository、UoW、数据库或 API。处理规则为：

- `REJECTED_LOCAL`：只保存幂等响应与当前只读 Frame，不推进 phase、beat、时钟、决策或版本。
- 本地查询：只返回权威查询结果与当前只读 Frame，不调用 Director 推进方法、不写快照或成功事件。
- 本地机械突变：仅提交 resolver 已确认的机械候选；Phase 2.2a 没有机械结果到剧情事实的映射，因此只重新规划 Frame，不猜测剧情结果。
- `NARRATIVE_REQUIRED`：返回 required/pending 与当前安全 Frame；没有 Provider 时不把意图当结果，不写事实、线索、时钟或 NPC 响应，版本不变。
- 当前声明式决策：`CHOOSE` 必须同时提交当前 Frame 公开的 `decision_id` 与其中一个 choice ID，且不能混入文本、target、tool 或其他结构化结算字段。公开 `decision_id` 是绑定 session、state version、scenario 内容版本与内部决策定义的确定性 token，不是可跨会话复用的 catalog ID。服务器策略验证 choice 后签发密封的 `player.decision.selected`，Director 才能记录该选择并执行内容包明确定义的决策转场/时间成本；选择本身不会声称 NPC 承认、线索发现或行动成功。
- 终局：普通叙事推进返回 `SCENARIO_ENDED`，安全结算 Frame 仍可读取。

可信剧情桥梁包含既有的决策响应 policy/issuer，以及 Phase 2.2c 独立的 `NarrativeOutcomePolicy`/`NarrativeEventIssuer`。两条 capability 都不可由玩家或 Provider 构造，并绑定 session、turn、request、action signature、state version、完整状态指纹和 scenario 内容版本；叙事 capability 还绑定 job、lease、内部 outcome rule 与 proposal digest。玩家 JSON、`PlayerAction`、普通 `VerifiedScenarioEvent`、模型自由文本或密封后修改的副本都不能通过真实性检查。特别地，玩家输入“护士承认我活着”只能匹配服务器声明的安全无效果规则，绝不会自行取得 NPC 承认权限。

成功决策在同一个深度隔离候选上形成剧情状态与稳定 `DomainEventDraft`，候选快照、连续事件、session 版本和幂等响应共用一个 `AsyncSession` 并只 commit 一次；任一步失败全部 rollback，一次成功回合 `state_version` 只增加一次。旧的 v1/v2 无 `scenario_runtime` 快照仍走兼容读取路径，不会补造场景副本。

公共行动响应不含 `action_signature`、快照、完整 `GameState`、Scenario 定义、隐藏事实、未来结局、密封信息或异常评估状态。`NarrativeFrame` 继续由 Director 从玩家已知事实、当前位置与真实 NPC 的安全交集构建；`/state` 的 `visible_npcs` 也使用同一类权威交集，而不是暴露全部 NPC。

Phase 2.2c 的 `NarrativeProvider` 仍只能提出候选叙事结果；只有锁内重新计算 token 集合并通过 policy 后，专用 issuer 才能从服务器模板签发可信事件。Provider 永远不能直接修改 `GameState`、事实、线索、时钟或决策。生产路径已可调用注入的模型，但仍没有 `DeviationEvaluator`、异常效果、场景崩坏、战斗系统或前端；默认测试只使用 Fake Provider，真实调用仍由显式 live 开关控制。

## Phase 2.2b-1 NarrativeProvider 与 DeepSeek V4

供应商无关模型位于 application：`NarrativeRequest` 只包含不可变安全 `NarrativeFrame` 副本、去除 session/turn/request 标识的规范化玩家意图、玩家可见职业标签、有界近期叙事、有界公开摘要、语言、版本化风格 ID 与 prompt schema 版本。它不包含 `GameState`、snapshot、`ScenarioDefinition`、隐藏事实、未来结局、策略 trace、action signature、capability、seal、数据库对象、API key 或供应商配置。

DeepSeek 依赖只存在于 infrastructure。当前默认模型是 `deepseek-v4-flash`，服务器可信配置可选择 `deepseek-v4-pro`；`deepseek-chat` 与 `deepseek-reasoner` 明确不允许。适配器固定使用官方 `https://api.deepseek.com/chat/completions`、`stream=false`、`response_format={"type":"json_object"}` 和 `thinking={"type":"disabled"}`，不提供工具、Web 搜索、Beta endpoint 或动态函数调用。完整边界见 [`docs/narrative_provider.md`](docs/narrative_provider.md)。

可选本地配置只从进程环境注入；模块导入不会读取 key、创建 client 或访问网络。`.env.example` 只提供空 key 和非敏感默认值：

```powershell
$env:DEEPSEEK_API_KEY = "<set-locally-without-committing>"
$env:DEEPSEEK_MODEL = "deepseek-v4-flash"
```

普通测试始终使用 Fake Transport；仅设置 key 仍不会调用 API。只有同时显式设置 opt-in 开关后，才运行独立的一次性安全烟雾测试：

```powershell
$env:RUN_LIVE_DEEPSEEK_TEST = "1"
.\.venv\Scripts\python.exe -m pytest tests\live\test_deepseek_live.py -m live -s
```

live 测试不连接 MySQL、不输出 key/请求头/完整 prompt/原始响应，且将传输重试固定为 0。模型返回的 JSON 始终先成为 `UntrustedNarrativeProposal`；`ValidatedNarrativeProposal` 只说明结构、引用、长度和公开范围通过检查。生产中的权威结果必须继续通过 Phase 2.2c 的锁内重算、policy、issuer 与 StoryDirector 信任链。
