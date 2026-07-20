# 玩家长期记忆（Phase 2.3b）

## 唯一事实来源

长期记忆只索引可信历史，不覆盖当前权威状态：

| 数据 | 唯一事实来源 |
|---|---|
| 当前属性 | `PlayerState.attributes` |
| 当前资源 | `PlayerState.resources` |
| 当前货币 | `WalletState` |
| 当前物品、数量和装备槽 | `InventoryState` |
| 当前技能及等级 | `PlayerState.skills` |
| 当前运行时 NPC、资源和关系数值 | `GameState.npcs` |
| 当前副本 phase、事实、线索、时钟、决策、ending 和精确 outcome 发生证据 | `ScenarioRuntimeState` |
| 完整持久化事件历史 | `domain_events` |
| 长期有界记忆索引 | `PlayerMemoryState` |

记忆不复制属性、资源、余额、库存、装备、技能、NPC runtime state、当前 phase/decision/threat clock、完整场景事实、Frame 或文学正文。

## 数据分类和稳定身份

`PlayerMemoryState.memory_model_version=2` 与 snapshot schema、内容包版本和 scenario 内容版本职责独立。`last_applied_source_sequence_no` 是最后成功投影的可信事件序号，不替代完整 `domain_events`；v1 memory payload 通过纯函数补充同步状态后迁移到 v2，`GameState.schema_version` 仍为 v3。

- `ScenarioMemoryRecord` 以 `scenario_id` 唯一标识，保存 scenario 内容版本、started/completed、可信 ending、封闭里程碑、公开事实引用及最后可信 event ID/sequence。同一副本更新原记录，不按回合追加。Phase 2.3b 继续把该键解释为单次生命周期身份：完成后再次进入相同 `scenario_id` 会明确失败；本阶段不支持副本重玩或多次 run。
- `NpcMemoryRecord` 只在 NPC 确实存在于 `GameState.npcs`，且其 definition 在当前玩家可见 location 中时建立。稳定 `subject_key` 使用带 `deviation-protocol:npc-subject:v1` 域标签的 `scenario_id + NUL + npc_definition_id` SHA-256 派生键；两个输入都必须通过禁止 NUL 的 `DefinitionId` 验证。runtime NPC ID 不持久化，catalog 存在也不等于玩家认识。如果同一场景运行时有多个 NPC 实例共用一个 definition，签发会明确失败而不是错误合并。
- `KnownPublicFactRecord` 只保存经当前权威 runtime 确认为玩家已知且不为 hidden 的事实引用，不复制事实值；记录和公开投影都携带 `scenario_id + fact_ref`，因此不同 scenario 复用 fact ID 时不会丢失语境。
- `SignificantExperienceEntry` 只有五种服务器枚举类别和对应固定 summary code，保存稳定 entry ID、有限 subject/fact 引用及可信事件引用，不保存模型摘要或正文。

## 更新、幂等与可信来源

所有写入先形成 `MemoryMutationPlan`。plan 使用进程内 issuer 标识并对全部记忆载荷、session ID、外部 state version、完整非记忆权威状态指纹、规范化 `ScenarioDefinition` 指纹及精确记忆前/后状态指纹计算摘要；普通构造、JSON/Pydantic 反序列化、`deepcopy`、pickle 往返和 seal 后嵌套改写都无法保留签发权威。plan 不能跨 session/version、跨不同权威状态、跨同版本但内容不同的 scenario definition，或在中间记忆变更后应用；同一计划只允许在其精确前状态生效，或在精确后状态作幂等重放。领域应用在独立候选 `PlayerMemoryState` 上完成所有检查，重新执行完整模型验证并核对封存后状态后，才一次替换 `GameState.player_memory`；失败前后完整 `GameState.to_snapshot()` 相等。

应用 factory 只接受进程内签发、不可普通构造的 `MemoryAuthoritySource` capability；普通 `DomainEvent`、JSON/Pydantic 数据或一个 `MemoryAuthorityEventType` 字符串都不能签发 plan。capability 只携带密封的 event/session/sequence/type envelope；factory 再从当前 runtime、scenario definition、运行时 NPC 和封闭枚举派生记忆字段，并忽略原 event payload。它不接受 `NarrativeFrame` 或公开文本作为授权输入。相同计划重复应用是幂等的；相同 stable key 的不同确认更新现有记录。实际改变记忆的 source sequence 必须严格递增；冲突 ID、倒序的新信息或容量溢出明确失败。

玩家/模型输入没有 memory、importance、relationship、milestone、ending、known fact、event ID/source/version 字段。`ActionSubmission`、`PlayerAction`、API body/query/header、`ActionContext`、`NarrativeFrame`、公开 summary、recent text、`continuity_notes`、`UntrustedNarrativeProposal` 和 `ValidatedNarrativeProposal` 都不能创建 plan 或直接修改记忆。`ValidatedNarrativeProposal` 仍只表示结构与公开引用验证通过。

生产写入从 `GameSessionRepository.persist_events()` 开始：Repository 在当前 UoW 内 insert 并 `flush` 事件行，成功后才返回不可普通构造的 `PersistedEventReceipt`。receipt 绑定 session、event ID、sequence、turn、目标 state version、event type 和规范 payload SHA-256；它只证明当前事务内已成功 flush，不证明之后 commit。Repository 不 commit，receipt 也不会序列化到 API、job、snapshot 或事件 payload。最终 rollback 会同时撤销 event、memory、snapshot、response、job 和 session version。

`ScenarioDefinition.memory_rules` 是可空、严格、声明式的可信内容目录。每条规则具有稳定 ID/version、封闭 source event type、必要的 outcome rule/event/result 或 completion 条件，以及一个封闭 operation；NPC、fact、ending、milestone、重要经历 category/summary 都只能引用已验证 catalog 内容或枚举。extra 字段、未知事件、重复规则、无效组合、不可达引用、脚本表达式和自由字段路径在加载时拒绝。匹配按 source sequence、再按 rule ID 稳定执行；同一事件触发的全部规则先在候选上完成，后置规则失败不会留下前序修改。普通事件字符串、模型 proposal 和内容包字段都不能签发 receipt 或 plan。

Session 创建在一个 UoW 内写 session、`ScenarioStarted` 事件、初始 memory 和 version-zero snapshot；重复或并发相同创建键从已提交 snapshot 重建同一 frame/memory，不再产生事件。确定性回合只有实际生成并匹配规则的可信事件才更新记忆；拒绝、查询和 narrative pending 不更新。Narrative finalize 只允许 `NarrativeEventIssuer` 的可信世界结果进入同一 event-flush/rule/plan 链，模型台词和 `continuity_notes` 永远不是记忆来源。

可信 narrative outcome 的 runtime 私有证据保存 `outcome_rule_id + outcome_result + scenario_event_type +` 服务器派生的 NPC definition targets。`NarrativeEventIssuer` 把这些字段绑定进密封事件，`StoryDirector` 在候选 runtime 中稳定排序、去重写入；它与 event、memory、snapshot、response、job 和 version 在 finalize 的同一事务提交，不进入 API、公开投影或 prompt。snapshot 完整性验证必须让 outcome 条件、event type、result 和 NPC target 同时匹配 memory rule；`applied_event_ids` 只继续承担事件重放去重，不能证明某一种 outcome result 已发生。

## 容量策略

状态硬上限如下：

- scenario records：64；
- NPC records：256；
- significant experiences：256；
- known public facts：512；
- 每条 scenario/NPC 的 milestone 或 fact refs：32；
- 每条 important experience 的 subject/fact refs：各 8。

达到任一容量时，触发该事件的全部 memory mutation 都不应用，索引从 `CURRENT` 进入 `REBUILD_REQUIRED`。状态记录最后成功 source event/sequence、第一个和最近 deferred sequence，以及上限为 1,000,000 的饱和 deferred count；不保存 deferred payload，完整历史仍在 `domain_events`。当前和后续正常游戏结果继续原子提交，但索引不会越过缺口伪装为 CURRENT；相同 deferred event 重放不重复计数。公开投影只显示 `complete=false` 和稳定同步状态，不公开缺口序号、数量或内容。只有 `MemoryCapacityError` 可降级为 lagging，非法规则、篡改、版本/顺序冲突和权限错误仍使事务失败。本阶段没有 rebuild、compaction 或压缩 worker。

## 快照兼容

当前 `GameState.schema_version=3`。迁移链为：

```text
snapshot v1 -> v2 (scenario_runtime = null) -> v3 (player_memory = explicit state)
memory model v1 -> v2 (CURRENT sync metadata)
```

迁移使用深拷贝，不修改输入。读取旧快照只产生空记忆，不根据 runtime、catalog 或旧正文回填经历；旧 v3/memory-v1 只补充可由原游标确定的 CURRENT 同步元数据。`ScenarioRuntimeState.narrative_outcome_evidence` 是 v3 内默认空的后向兼容字段，因此不提升 snapshot schema：旧 v1/v2/v3 在没有相应动态记忆时继续加载；旧 snapshot 若声称 outcome 条件 fact、NPC、ending、milestone 或 experience，却没有精确发生证据，则严格按非法 snapshot 拒绝。v3 严格拒绝 bool/float/string schema version、extra 字段、非法或内容不匹配的派生 ID、孤立 scenario/fact 索引、不一致的顺序/lagging 标记、重复记录、越界集合和非 JSON 值。状态仍写入现有 `game_snapshots.state_json`；ORM 和 Alembic 无变化。

## 公开投影与 Provider 边界

`PlayerMemoryProjector` 先 JSON 往返隔离源状态，再输出 frozen tuple DTO。集合上限为 16 scenarios、32 NPCs、64 experiences、128 facts；总字符不超过 16,000，规范 UTF-8 JSON 不超过 32,000 bytes。超限时按可信 sequence 保留较新的记录并用 `truncated` 与总数明确标记，最终输出再按稳定 ID 排序。投影剥离 source event ID/sequence、deferred metadata、receipt、seal、capability 和 rule ID，只含已确认的玩家已知引用。它同时进入只读玩家状态 API 和 `NarrativeRequest`；prepare/finalize 用 state version、state fingerprint 和 request fingerprint 重新绑定、重算并比较。

`PromptBuilder` 只把投影放入规范 JSON 数据区，不拼接为 system instruction；总 prompt 仍受字符和 UTF-8 byte 双重硬上限，超限在 Provider transport 前失败。Provider 输出、ValidatedProposal 和 continuity notes 都没有记忆写权限。生产没有任何玩家/模型 memory mutation API。本阶段不实现向量数据库、Embedding、RAG、记忆模型调用、rebuild/compaction worker、前端、战斗或 `DeviationEvaluator`。

当前 NPC identity 也有意保持局部：同一 definition 跨 scenario 会形成不同 subject；scenario content version 改变时旧记录会冲突；本阶段不建立跨世界/跨版本人物身份。只有副本包含重大隐藏设定、关键 NPC、新路线或明确二周目价值时，未来才值得先设计显式 `scenario_run_id` 和稳定 subject identity；普通已完成副本不为无意义回收而提供重入。

完整性验证始终按每条记录自己的 `scenario_id` 和 `scenario_content_version` 选择 catalog 定义，不把所有记录解释为当前副本。当前系统没有独立、持久化的跨 scenario participation history，因此任何非空 `ScenarioMemoryRecord` 都必须先有同 `scenario_id`、同内容版本的权威 `ScenarioRuntimeState` 证明玩家已进入该 scenario；缺少匹配 runtime 的记录严格拒绝。只有 participation 独立成立后，catalog 中 `PLAYER_KNOWN` 的初始公开 fact 才可免于额外动态发现事件；它不能反过来证明 participation。DISCOVERABLE fact、NPC occurrence、ending、动态 milestone 和 significant experience 仍必须有同 scenario 的 runtime 状态或精确 outcome 证据。未来若支持历史 scenario，必须新增独立的权威 participation evidence，不能由 `ScenarioMemoryRecord`、公开 fact 或某条 `MemoryRule` 降级推断。

Phase 2.3b 也不把 `ScenarioRuntimeState.dynamic_facts` 写入长期记忆；因此玩家/模型不能借 `dynamic.*` 自由键跨越 fact identity 与长度边界。FIXED/DEFERRED/MUTABLE 事实同样只保存引用，不保存可能过期的值；后续消费者若需要当前值，仍必须回到当前权威 scenario runtime/content，而不能把记忆引用解释成第二份当前真相。
