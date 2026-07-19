# NarrativeProvider 边界（Phase 2.2c）

## Phase 2.2c production boundary

Production uses `DurableNarrativeTurnOrchestrator` with three database phases. Prepare holds the session row lock only while checking idempotency, snapshot/catalog compatibility, Gateway/RuleResolver, the safe frame, declarative outcome candidates, and the bounded request; it commits PREPARED and closes the UoW. Claim holds only the job row long enough to mint a server lease and commit. `NarrativeProvider.generate()` is then called with no active UoW, `AsyncSession`, session lock, or job lock. A validated proposal is persisted promptly in a fresh short transaction. Finalize locks session then job, revalidates every binding and lease, and atomically commits text plus authoritative state.

External HTTP latency must not retain MySQL locks: otherwise a seconds-long model call would block safe same-session reads, enlarge deadlock windows, and tie database connection capacity to provider latency. Real MySQL tests acquire the same session row from inside a delayed Fake Provider, execute a local query during the wait, deduplicate the same request, and allow different sessions to enter the provider concurrently.

`narrative_jobs` records job/session/turn/request/action signature, prepared state version and fingerprint, scenario/content version, safe request/fingerprint, prompt/style version, provider/model names, status, a single job invocation attempt, lease, validated proposal subset, stable error, and timestamps. It does not record the API key, Authorization, complete prompt, raw response, or reasoning. `PREPARED`, `IN_PROGRESS`, `PROPOSAL_VALIDATED`, and `COMMITTED` are the normal states; `FAILED_RETRYABLE`, `FAILED_TERMINAL`, `STALE`, and `OUTCOME_UNKNOWN` make failures explicit. Once a provider may have started but the result/charge is uncertain, the job is not automatically resent. An expired PROPOSAL_VALIDATED job instead receives a new finalize-only fenced lease and continues without Provider. Expired and old lease holders cannot save a proposal, finalize, or change the job.

Declarative `NarrativeOutcomeRuleDefinition` entries contain a stable/versioned rule ID, phases, bounded action matcher, visible-NPC and fact/clue/decision preconditions, once/repeat semantics, safe public description, fixed effect templates, server action/time cost, priority, and mutex group. Catalog loading rejects missing references, unreachable decision bindings, invalid fixed effect values, and ambiguous mutex priorities. There is no eval/exec/import/expression language, arbitrary setattr, model-supplied delta/fact/clue/event payload, inventory/equipment/skill/currency/resource/attribute/NPC-existence change, FIXED-fact rewrite, or anomaly route.

For each request the server maps an eligible internal rule to an opaque token bound to session/turn/request, action signature, state version/fingerprint, scenario/version, and frame. The model returns only that token, a permitted result category, already-public entity references, bounded NPC utterances, prose, and non-authoritative continuity notes. Finalize recomputes the token set; string equality alone never grants authority. `NarrativeOutcomePolicy` validates route/job/state/action/token/visibility/preconditions/result/prose/mutex and internally mints a capability. Its prose check is a conservative structural boundary using visible speakers and data-defined required/forbidden terms, not a complete semantic truth checker. NPC dialogue and narrative text never establish facts. `NarrativeEventIssuer` rechecks job/lease/all bindings and proposal digest, then derives a sealed `VALIDATED_NARRATIVE_OUTCOME` event only from the server template. StoryDirector remains the sole fact/clue/clock/decision mutation engine.

PROPOSAL_VALIDATED persists the bounded `ValidatedNarrativeProposal`, including candidate narrative text, for crash recovery. This is validated-but-unaccepted internal data, not an assertion that the scene happened. It cannot be read through player APIs or projections and is excluded from recent context, prompts, snapshots, facts, NPC knowledge, and summaries. STALE, FAILED, and OUTCOME_UNKNOWN jobs may retain candidate prose until job/session deletion; there is no Phase 2.2c cleanup worker, and retention does not promote it to authoritative memory. Accepted prose becomes player-visible only after the same commit that stores snapshot, events, response, accepted text, COMMITTED job, and session version. Stale, rejected, CAS-failed, or rolled-back prose is not returned and never enters recent context.

## 责任与数据流

`NarrativeProvider` 是 application 层的供应商无关 Protocol。调用方只能构造 `NarrativeRequest`，其数据来源限定为安全 `NarrativeFrame` 的不可变副本、已通过本地行动边界的规范化玩家意图、玩家可见角色标签、最多 6 个近期已接受叙事片段、最多 2,000 字符公开摘要，以及语言、style profile ID 和 prompt schema version。

请求绝不会包含完整 `GameState`/snapshot、`ScenarioDefinition`/catalog、隐藏事实、未发现线索、未来地点或结局、NPC 秘密、action signature、policy trace、capability、seal、数据库对象、API key、供应商配置或参考作品原文。Chat Completions 是无状态接口；适配器不会假设服务端保存任何玩家历史，也不会发送完整事件流或副本 JSON。

`PromptBuilder` 与供应商适配器分离。同一输入和同一 profile 构建完全相同的 prompt。默认 profile `original-zh-second-person-v1@1.0.0` 只包含简洁原创风格约束，不含题材专属内容或长篇示例。玩家文本放在 `INPUT_DATA_JSON.untrusted_player_intent` 数据段；公开摘要和近期正文也明确只是数据，任何一项都不能改变 system 规则。规范 JSON 会转义可伪造分隔符的尖括号。

## 不可信与已验证候选

DeepSeek JSON 先解析为 `NarrativeProposalPayload`，再由应用包装为 `UntrustedNarrativeProposal`。严格字段只有：

- `schema_version`
- `narrative_text`
- `referenced_entity_ids`
- 有界 `npc_utterances`
- 封闭类型的 `untrusted_outcome_proposals`
- 有界、非权威 `continuity_notes`

所有模型字段禁止 extra，并有字符串、集合和正文上限。模型不能声明 provider metadata；适配器只记录安全的 provider、配置模型、request ID、finish reason、attempt 数、整数 latency 和实际存在的 usage 字段。

`NarrativeProposalValidator` 使用当前 Frame 与权威公开引用集合验证结构、引用、可见 NPC speaker、玩家拥有且已公开的物品、长度和内部数据泄漏形态。通过后得到的 `ValidatedNarrativeProposal` 仍只是可展示候选：它不代表 NPC 已承认某事，不把玩家声称的结果变成世界结果，也没有创建事件、修改 `GameState` 或取得 issuer capability 的接口。

## DeepSeek V4 配置

当前官方 OpenAI 兼容配置：

- base URL：`https://api.deepseek.com`
- endpoint：`/chat/completions`
- 默认 model：`deepseek-v4-flash`
- 可选 model：`deepseek-v4-pro`
- thinking：`{"type":"disabled"}`
- JSON：`{"type":"json_object"}`
- stream：`false`

`deepseek-chat` 和 `deepseek-reasoner` 不在配置枚举中。官方文档说明它们将在 2026-07-24 退役；本仓库不依赖兼容别名。参见 [DeepSeek V4 更新说明](https://api-docs.deepseek.com/updates/)、[Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/) 和 [JSON Output](https://api-docs.deepseek.com/guides/json_mode/)。

配置仅在显式调用 `DeepSeekSettings.from_environment()` 时读取进程环境；模块导入不会读取 key、创建 client 或联网。默认 timeout 30 秒、max output 1,200 tokens、0 retry（一次 HTTP attempt）；运维可显式配置最多 2 次 retry（总共最多 3 次 attempt），且配置模型进一步限制 timeout、token 与 retry 上界。玩家请求无法覆盖这些值。

错误映射与重试：

- 400/422：请求参数错误，不重试。
- 401：认证失败，不重试。
- 402：余额不足，不重试。
- 429、500、503：仅在显式启用 retry 时做有界指数退避。
- 连接失败和 timeout：仅在显式启用 retry 时做有界指数退避；read timeout 或连接中断不能证明请求未到达供应商。
- 空 content 或 JSON 解析失败：最多一次受控重试，并受总尝试数限制。
- `finish_reason=length`：截断失败，不接受局部 JSON。
- 其他状态、finish reason 或响应形状：固定 provider 失败。

等待器与传输均可注入，离线测试不会真实 sleep 或访问网络。错误字符串、repr、日志与 DTO 不包含 API key、Authorization、完整 prompt、完整原始 response 或供应商异常文本。

一次 job claim、一次 `NarrativeProvider.generate()` invocation、一次 HTTP transport attempt 与一次供应商计费不是同一概念。Job 只允许一次 Provider invocation，但显式配置的 adapter retry 可令该 invocation 发出最多三次 HTTP 请求。客户端既不能可靠判断某次超时请求是否已经到达供应商，也不能证明供应商实际计费次数；因此本实现不宣称 exactly-once billing，并避免 job retry 与 adapter retry 相乘。

## 可选 live smoke

默认 `pytest` 不访问网络。测试只有在进程环境同时满足 `DEEPSEEK_API_KEY` 存在且 `RUN_LIVE_DEEPSEEK_TEST=1` 时才运行；仅存在 key 仍会 skip。smoke 固定 `deepseek-v4-flash`、thinking disabled、non-stream、较小 token 上限、0 retry，只发送一次微型玩家安全 Frame，不创建 engine、不连接 MySQL，并要求响应通过 `NarrativeProposalValidator`。

```powershell
$env:RUN_LIVE_DEEPSEEK_TEST = "1"
.\.venv\Scripts\python.exe -m pytest tests\live\test_deepseek_live.py -m live -s
```

live smoke 成功时只显示安全正文和最小诊断元数据；生产 API 不返回 model/usage。失败只报告稳定错误码。
