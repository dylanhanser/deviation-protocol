# NarrativeProvider 边界

## Current Provider concepts

`NarrativeProvider` is the supplier-neutral application interface. Its current
responsibility is deliberately narrow: receive one validated, bounded
`NarrativeRequest`; return one untrusted narrative proposal and safe Provider
metadata; and release its own resources through `aclose()`. It does not choose
the Provider route, own credentials, authorize outcomes, mutate state, or
persist a completion.

Normal `deviation_protocol.api.main:app` composition configures the
infrastructure `DeepSeekNarrativeProvider` only when valid server-side DeepSeek
settings exist. Otherwise Narrative work reaches the existing explicit
not-configured boundary. The adapter renders the application request through
the current versioned style profile, calls the configured DeepSeek model, and
parses the response as an untrusted proposal. Normal composition never silently
falls back to the deterministic Demo Provider.

Phase 3.2a implements `DeterministicDemoNarrativeProvider` only in the
independent `deviation_protocol.api.demo:app` composition. It is a pure,
secrets-free function of the validated request and remains behind the normal
validator, outcome policy, trusted issuer, and StoryDirector. It is isolated
from normal Provider configuration and from any future commercial
distribution.

Provider selection and narrative authority are separate:

- a Provider or model channel selects where candidate prose is generated;
- the model narrates confirmed state and results;
- the engine and trusted server policies own objective mechanics, resources,
  facts, clocks, relationship progression, permanent state, and canon; and
- style settings change presentation only and cannot rewrite established
  facts.

## Future Provider and narrative controls

Phase 4.0's accepted design introduces a self-controlled **Production
Distribution Gateway** for explicit player-selected Provider/model channels,
server-side credentials, quota, metering, rate limiting, and abuse control.
That network component is not the application `NarrativeProvider` interface and
is not implemented. Its canonical decision is
[ADR 0001](decisions/0001-production-provider-distribution.md).

Phase 3.3's approved [Run Protocol design](run_protocol.md) will add structured,
versioned presentation controls after engine-owned difficulty, character, and
permitted pre-game overrides are resolved. No `RUN_PROTOCOL` block exists in
the implemented prompt today.

Phase 3.4's approved
[NPC Relationship and Temporary Residence design](npc_relationship_residence.md)
will permit bounded residence conversation under engine authority. Residence
mode is not implemented. Future relationship dialogue may express established
personality and confirmed shared memories, but it cannot independently upgrade
relationships, create permanent promises, reveal major secrets, or change
canon.

## Phase 2.4b public playtest boundary

`ActionType.CONTINUE` 不属于 Narrative Provider 输入。它只在锁内重载的权威 Frame 为 CONTINUE、scenario 为 ACTIVE 且不存在当前 decision 时，通过 StoryDirector 的空事件路径推进一个 auto beat。CONTINUE 不创建 PREPARED job、不 claim lease、不构造 prompt、不调用 `NarrativeProvider.generate()`。最小成功路径与 MySQL 成功 playtest 的 Provider 调用固定为 5 次；内存 E2E 为验证直接猜测隐藏真相只能得到 no-effect，额外调用一次，合计 6 次；deadline playtest 固定为 7 次。CONTINUE、CHOOSE、查询、duplicate replay 和本地拒绝的 Provider 调用均为零。

`GET /v1/sessions/{session_id}/requests/{client_request_id}` 是 narrative job 的玩家安全只读投影，不是 job 调试接口。查询优先读取已提交 TurnResponse；PENDING 覆盖 PREPARED、IN_PROGRESS 与 PROPOSAL_VALIDATED，但即使后者已持久化 candidate prose，响应也只含状态、固定 retry 秒数和客户端动作，不含 proposal。STALE 与 OUTCOME_UNKNOWN 分别使用 `NARRATIVE_REQUEST_STALE/REFRESH_VIEW` 和 `NARRATIVE_OUTCOME_UNKNOWN/DO_NOT_RETRY`，不能互换。FAILED 不透传 Provider、model、usage 或内部 error detail；遗留 FAILED_RETRYABLE 与当前 FAILED_TERMINAL 都公开为 `FAILED/DO_NOT_RETRY`。公共协议不返回 RETRY_WITH_NEW_REQUEST。

状态查询和 `GET /view` 都不 claim 或延长 lease、不调用 Provider、不改变 job/snapshot/version。Provider 尚在处理时，view 从最新已提交 snapshot 重算 Frame，因此不会显示候选正文或假定结果；只有 finalize 原子提交后的 accepted text 才进入 view 的近期正文。

## Phase 2.3b production boundary

Production uses `DurableNarrativeTurnOrchestrator` with three database phases. Prepare holds the session row lock only while checking idempotency, snapshot/catalog compatibility, Gateway/RuleResolver, the safe frame, declarative outcome candidates, and the bounded request. It also creates a public `PlayerMemoryProjection` and binds the request to the locked state version/fingerprint before committing PREPARED and closing the UoW. Claim holds only the job row long enough to mint a server lease and commit. `NarrativeProvider.generate()` is then called with no active UoW, `AsyncSession`, session lock, or job lock. A validated proposal is persisted promptly in a fresh short transaction. Finalize locks session then job, revalidates every binding and lease, recomputes the memory projection/request, and atomically commits accepted text plus authoritative state, flushed events and deterministic memory.

External HTTP latency must not retain MySQL locks: otherwise a seconds-long model call would block safe same-session reads, enlarge deadlock windows, and tie database connection capacity to provider latency. Real MySQL tests acquire the same session row from inside a delayed Fake Provider, execute a local query during the wait, deduplicate the same request, and allow different sessions to enter the provider concurrently.

`narrative_jobs` records job/session/turn/request/action signature, prepared state version and fingerprint, scenario/content version, safe request/fingerprint, prompt/style version, provider/model names, status, a single job invocation attempt, lease, validated proposal subset, stable error, and timestamps. It does not record the API key, Authorization, complete prompt, raw response, or reasoning. `PREPARED`, `IN_PROGRESS`, `PROPOSAL_VALIDATED`, and `COMMITTED` are the normal states; current failures transition only to `FAILED_TERMINAL`, `STALE`, or `OUTCOME_UNKNOWN`. `FAILED_RETRYABLE` remains an internal legacy-compatible enum with no production transition. Once a provider may have started but the result/charge is uncertain, the job is not automatically resent. An expired PROPOSAL_VALIDATED job instead receives a new finalize-only fenced lease and continues without Provider. Expired and old lease holders cannot save a proposal, finalize, or change the job.

最终确定性 CHOOSE 不调用 Provider，但其固定服务器结算正文仍以一个受限的 `local-server-template-v1` COMMITTED job 加入结束事务。该 job 只能是 attempt=0、无 lease、无 error、固定 provider/model sentinel，并且 accepted text 与 validated local template 同时存在；其他字段组合由模型验证拒绝。它使 ending event、completion memory、snapshot、response、正文、job 与 version 具备同一 rollback 边界，不把本地选择伪装成模型调用。

Declarative `NarrativeOutcomeRuleDefinition` entries contain a stable/versioned rule ID, phases, bounded action matcher, visible-NPC and fact/clue/decision preconditions, once/repeat semantics, safe public description, fixed effect templates, server action/time cost, priority, and mutex group. Catalog loading rejects missing references, unreachable decision bindings, invalid fixed effect values, and ambiguous mutex priorities. There is no eval/exec/import/expression language, arbitrary setattr, model-supplied delta/fact/clue/event payload, inventory/equipment/skill/currency/resource/attribute/NPC-existence change, FIXED-fact rewrite, or anomaly route.

Phase 2.4b templates may also contain fixed `opened_location_ids`, `new_location_id`, and required current-location IDs. Catalog loading requires every referenced location to exist, every required current location to be visible in every allowed phase, and every destination to be visible in every allowed phase. The first investigation decision itself opens and enters the records room; subsequent clue rules require the authoritative current location plus mechanical `OBSERVE`/`EXPLORE`. Only sealed server events carry location or clue effects; proposal JSON and player text carry none. When a public decision is open, ordinary Narrative rules are ineligible unless they bind that exact decision and every result resolves it, preventing fallback prose from bypassing CHOOSE.

For each request the server maps an eligible internal rule to an opaque token bound to session/turn/request, action signature, state version/fingerprint, scenario/version, and frame. The model returns only that token, a permitted result category, already-public entity references, bounded NPC utterances, prose, and non-authoritative continuity notes. Finalize recomputes the token set; string equality alone never grants authority. Before authorization, the proposal validator rejects internal rule/outcome/job/lease/receipt/provider/model markers, the exact opaque tokens in the request, future ending/internal ID shapes, long secret-like values, and non-public references from prose, utterances, and continuity notes. `NarrativeOutcomePolicy` then validates route/job/state/action/token/current-location/visibility/preconditions/result/prose/mutex and internally mints a capability. Every production effect supplies fixed public narrative text; validated candidate prose cannot override or contradict that accepted text. `NarrativeEventIssuer` rechecks job/lease/all bindings and proposal digest, then derives a sealed `VALIDATED_NARRATIVE_OUTCOME` event only from the server template. StoryDirector remains the sole fact/clue/clock/decision mutation engine.

PROPOSAL_VALIDATED persists the bounded `ValidatedNarrativeProposal`, including candidate narrative text, for crash recovery. This is validated-but-unaccepted internal data, not an assertion that the scene happened. It cannot be read through player APIs or projections and is excluded from recent context, prompts, snapshots, facts, NPC knowledge, and summaries. STALE, FAILED, and OUTCOME_UNKNOWN jobs may retain candidate prose until job/session deletion; there is no Phase 2.2c cleanup worker, and retention does not promote it to authoritative memory. Accepted prose becomes player-visible only after the same commit that stores snapshot, events, response, accepted text, COMMITTED job, and session version. Stale, rejected, CAS-failed, or rolled-back prose is not returned and never enters recent context.

## 责任与数据流

`NarrativeProvider` 是 application 层的供应商无关 Protocol。调用方只能构造 prompt schema v2 的 `NarrativeRequest`，其数据来源限定为安全 `NarrativeFrame` 的不可变副本、公开且有界的 `PlayerMemoryProjection`、已通过本地行动边界的规范化玩家意图、玩家可见角色标签、最多 6 个近期已接受叙事片段、最多 2,000 字符公开摘要，以及语言和 style profile ID。记忆投影最多 16 scenarios、32 NPCs、64 experiences、128 public facts，同时受 16,000 字符和 32,000 UTF-8 bytes 上限约束；可能包含 `complete=false`/`REBUILD_REQUIRED`，但不包含 deferred 数量或内容。

请求绝不会包含完整 `GameState`/`PlayerMemoryState`/snapshot、`ScenarioDefinition`/catalog、domain events、source event ID/sequence、deferred metadata、memory rule ID、receipt/capability/seal、隐藏事实、未发现线索、未来地点或结局、NPC 秘密、action signature、policy trace、数据库对象、API key、供应商配置或参考作品原文。Chat Completions 是无状态接口；适配器不会假设服务端保存任何玩家历史，也不会发送完整事件流或副本 JSON。

`PromptBuilder` 与供应商适配器分离。同一输入和同一 profile 构建字节级相同的 prompt。默认 profile `original-zh-second-person-v1@1.0.0` 只包含简洁原创风格约束，不含题材专属内容或长篇示例。玩家文本放在 `INPUT_DATA_JSON.untrusted_player_intent`，公开摘要、近期正文和 memory projection 都位于 `server_public_context` 的规范 JSON 数据区，任何一项都不能成为 system instruction；`complete=false` 也不表示授权。规范 JSON 执行 NFC、稳定集合排序、key 排序并转义可伪造分隔符的尖括号。User prompt 上限为 32,000 字符，总 prompt 上限为 32,000 字符和 64,000 UTF-8 bytes；超限在 transport/provider token 消耗前拒绝。

升级前已是 `PREPARED`、`IN_PROGRESS` 或 `PROPOSAL_VALIDATED` 的 prompt-v1 job 不会由新代码解析或 finalize，也不会自动再次调用 Provider；命中同一请求时会稳定转为 `STALE/NARRATIVE_REQUEST_SCHEMA_STALE`，客户端需使用新的 `client_request_id`。旧 job 的 prompt/proposal/provider error 不出现在安全错误中。已经 `COMMITTED` 的旧 job 仍先读取持久化 turn response，保持现有幂等语义，不重新生成。

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

Proposal schema 没有 memory operation、importance、summary code、relationship、milestone 或 fact ID 授权字段；extra 字段会被拒绝。`continuity_notes` 只用于候选连续性，永远不进入 `PlayerMemoryState`。Finalize 中只有 outcome policy 重新授权后由 `NarrativeEventIssuer` 产生、并在当前 UoW insert/flush 的可信世界事件，才可以匹配声明式 `MemoryRule`。因此玩家文本或模型台词声称 NPC 已承认玩家存活不会写记忆；只有既有 outcome rule 的 SUCCESS 与 `vitals.verified` 可信结果能够触发对应固定规则。

`death_certificate` 的临床复核模板固定声明作出存活承认的 runtime NPC，并附加服务器所有的公开承认文本；Provider utterance、references 和正文都不能选择或证明该 NPC authority。权威证据是 `NarrativeOutcomeAccepted` 中由服务器模板派生的 rule/result/scenario-event/NPC/acknowledgement 组合，随后由 StoryDirector 写入 runtime evidence 并由 memory rule 消费。记录、审计和患者路线分别要求普通动作词与路线主题词，授予固定 clues 与地点；直接陈述隐藏结论或阶段 no-effect fallback 不授予任何必需线索、地点、核心事件或 ending，且 no-effect 正文由服务器固定。

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

配置仅在显式调用 `DeepSeekSettings.from_environment()` 时读取进程环境；模块导入不会读取 key、创建 client 或联网。默认 timeout 30 秒、max output 4,096 tokens、0 retry（一次 HTTP attempt）；运维可显式配置最多 2 次 retry（总共最多 3 次 attempt），且配置模型进一步限制 timeout、token 与 retry 上界。4,096-token 默认值来自一次已确认的 Dynamic Narrative Live 截断：原 1,200-token 默认值在严格候选完成前得到 `finish_reason=length`。该修正只扩展既有有限输出预算；截断仍直接失败，且玩家请求无法覆盖这些值。

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

## Experimental dynamic Provider boundary

The DNVS candidate reuses `DeepSeekSettings`, the existing DeepSeek transport,
HTTP client ownership, and shutdown path. Its additive application Protocol is
exactly `generate_dynamic(DynamicNarrativeRequest) ->
UntrustedDynamicNarrativeCandidate` plus `aclose()`. The dynamic adapter builds
one bounded prompt, performs exactly one transport call, accepts only one strict
JSON object with no floats or duplicate keys, and returns no authoritative
capability. Dynamic composition refuses any settings whose `max_retries` is not
zero, so no layer can recreate a job, repeat a Provider invocation, or retry a
transport request automatically.

`DEVIATION_DEMO_DYNAMIC_PROVIDER` is a composition selector, not Provider
configuration. Missing or exact `fake` selects the bounded deterministic Fake;
only exact explicit `live` constructs DeepSeek settings and transport. Empty or
invalid selection, invalid Live settings, or Fake construction failure fails
closed and never falls back. Credentials never select a mode and are never sent
to the Web child. Fake reads no Provider variable and constructs no transport.

Explicit Live Demo composition wraps the selected adapter in a private
process-local observational counter. A new wrapper, which in normal operation
means a new launcher process and in tests means a new fixture/runtime, starts at
zero; the wrapper exposes a synchronized process-local read and no in-place
reset operation. Its private accessor is `wrapper_attempt_count`. Each call that
passes the wrapper's closed check increments once at the wrapper-attempt
boundary, before evidence emission and Provider delegation, then attempts to
emit only this secret-free diagnostic shape:

```text
DNVS_LIVE_EVIDENCE event=wrapper_attempt ordinal=<positive-decimal> cumulative_wrapper_attempts=<same-positive-decimal>
```

An ordinary `Exception` raised by that evidence output is
non-propagating, and the delegate is still invoked exactly once.
`asyncio.CancelledError`, `KeyboardInterrupt`, `SystemExit`, and other
`BaseException` subclasses retain normal Python semantics: the exact original
exception propagates, and when evidence emission raises it before delegation,
the delegate is not invoked. The counter is not rolled back, so the first such
interrupted wrapper attempt leaves it at one; it is not evidence of delegate
entry, Provider dispatch, remote Provider receipt, billing, or generation
completion. The delegate's original return value, ordinary exception, or
cancellation propagates unchanged, and instrumentation introduces neither a
retry nor another generation.

The counter and evidence are non-persistent, secret-free, non-authoritative,
and outside every public API, persistence, billing, retry, and gameplay-state
contract. They record no credential, prompt, response body, private memory, or
private fact. Concurrent increments and reads are synchronized so the total is
the number of wrapper attempts that passed the closed check in that wrapper
lifetime. Ordinary evidence-output failure cannot prevent or duplicate
dispatch; process-control propagation cannot trigger dispatch, retry, or
recovery generation. Neither category changes application generation policy.

The automated dynamic live smoke remains separately authorized: it is exactly
one real Provider call and zero retries. Manual Fake browser evidence is exactly
eight submitted actions and zero real calls; Optional Live browser evaluation,
if separately authorized, is exactly eight requests. None of those activities
is implied by the current unstaged implementation candidate or by its Offline
tests.

The Dynamic Narrative Live adapter uses the same bounded 4,096-token default.
A terminal `finish_reason=length` emits only
`DNVS_LIVE_DIAG_TERMINAL_RESPONSE_TRUNCATED`; it does not expose content or
authorize an application replacement, transport retry, partial acceptance, or
schema relaxation.
