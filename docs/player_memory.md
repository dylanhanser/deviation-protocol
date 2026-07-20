# 玩家长期记忆（Phase 2.3a）

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
| 当前副本 phase、事实、线索、时钟、决策和 ending | `ScenarioRuntimeState` |
| 完整持久化事件历史 | `domain_events` |
| 长期有界记忆索引 | `PlayerMemoryState` |

记忆不复制属性、资源、余额、库存、装备、技能、NPC runtime state、当前 phase/decision/threat clock、完整场景事实、Frame 或文学正文。

## 数据分类和稳定身份

`PlayerMemoryState.memory_model_version=1` 与 snapshot schema、内容包版本和 scenario 内容版本职责独立。`last_applied_source_sequence_no` 只是记忆索引内部的确定性乱序保护，不是完整事件游标，也不替代 `domain_events`。

- `ScenarioMemoryRecord` 以 `scenario_id` 唯一标识，保存 scenario 内容版本、started/completed、可信 ending、封闭里程碑、公开事实引用及最后可信 event ID/sequence。同一副本更新原记录，不按回合追加。Phase 2.3a 将该键解释为单次生命周期身份：完成后再次进入相同 `scenario_id` 会明确失败；本阶段不声称支持副本重玩或多次 run。
- `NpcMemoryRecord` 只在 NPC 确实存在于 `GameState.npcs`，且其 definition 在当前玩家可见 location 中时建立。稳定 `subject_key` 使用带 `deviation-protocol:npc-subject:v1` 域标签的 `scenario_id + NUL + npc_definition_id` SHA-256 派生键；两个输入都必须通过禁止 NUL 的 `DefinitionId` 验证。runtime NPC ID 不持久化，catalog 存在也不等于玩家认识。如果同一场景运行时有多个 NPC 实例共用一个 definition，签发会明确失败而不是错误合并。
- `KnownPublicFactRecord` 只保存经当前权威 runtime 确认为玩家已知且不为 hidden 的事实引用，不复制事实值；记录和公开投影都携带 `scenario_id + fact_ref`，因此不同 scenario 复用 fact ID 时不会丢失语境。
- `SignificantExperienceEntry` 只有五种服务器枚举类别和对应固定 summary code，保存稳定 entry ID、有限 subject/fact 引用及可信事件引用，不保存模型摘要或正文。

## 更新、幂等与可信来源

所有写入先形成 `MemoryMutationPlan`。plan 使用进程内 issuer 标识并对全部记忆载荷、session ID、外部 state version、完整非记忆权威状态指纹、规范化 `ScenarioDefinition` 指纹及精确记忆前/后状态指纹计算摘要；普通构造、JSON/Pydantic 反序列化、`deepcopy`、pickle 往返和 seal 后嵌套改写都无法保留签发权威。plan 不能跨 session/version、跨不同权威状态、跨同版本但内容不同的 scenario definition，或在中间记忆变更后应用；同一计划只允许在其精确前状态生效，或在精确后状态作幂等重放。领域应用在独立候选 `PlayerMemoryState` 上完成所有检查，重新执行完整模型验证并核对封存后状态后，才一次替换 `GameState.player_memory`；失败前后完整 `GameState.to_snapshot()` 相等。

应用 factory 只接受进程内签发、不可普通构造的 `MemoryAuthoritySource` capability；普通 `DomainEvent`、JSON/Pydantic 数据或一个 `MemoryAuthorityEventType` 字符串都不能签发 plan。capability 只携带密封的 event/session/sequence/type envelope；factory 再从当前 runtime、scenario definition、运行时 NPC 和封闭枚举派生记忆字段，并忽略原 event payload。它不接受 `NarrativeFrame` 或公开文本作为授权输入。相同计划重复应用是幂等的；相同 stable key 的不同确认更新现有记录。实际改变记忆的 source sequence 必须严格递增；冲突 ID、倒序的新信息或容量溢出明确失败。

玩家/模型输入没有 memory、importance、relationship、milestone、ending、known fact、event ID/source/version 字段。`ActionSubmission`、`PlayerAction`、API body/query/header、`ActionContext`、`NarrativeFrame`、公开 summary、recent text、`continuity_notes`、`UntrustedNarrativeProposal` 和 `ValidatedNarrativeProposal` 都不能创建 plan 或直接修改记忆。`ValidatedNarrativeProposal` 仍只表示结构与公开引用验证通过。

Phase 2.3a 只定义事件引用边界，不声称用于签发 capability 的 `DomainEvent` 已经持久化。plan factory、`MemoryAuthoritySource` 及内部 capability 签发 seam 都不从 `deviation_protocol.application` 包顶层导出，也未注入任何生产服务；进程内 capability 只阻断数据反序列化伪造，不等于持久化证明。Phase 2.3b 接线必须在同一受控事务和会话锁中，从真实持久化事件/可信结果建立 source，传入实际 session/state version，并原子保存快照；不能把 capability/factory 暴露给 API 或复制玩家/模型字段。

## 容量策略

状态硬上限如下：

- scenario records：64；
- NPC records：256；
- significant experiences：256；
- known public facts：512；
- 每条 scenario/NPC 的 milestone 或 fact refs：32；
- 每条 important experience 的 subject/fact refs：各 8。

达到容量时，已有键仍可幂等读取或在限额内更新；新增不同记录在签发完成前抛出 `MemoryCapacityError`，原状态不变。本阶段不静默淘汰、不无限 append，也没有声称已解决未来无限期压缩。特别是 256 条 important experience 满额后会拒绝新条目；Phase 2.3b 不能未经产品化容量处置就把该失败直接变成正常游戏的阻断点。之后若需要压缩，必须另建可信、确定性的显式流程。

## 快照兼容

当前 `GameState.schema_version=3`。迁移链为：

```text
v1 -> v2 (scenario_runtime = null) -> v3 (player_memory = explicit empty state)
```

迁移使用深拷贝，不修改 v1/v2 输入。读取旧快照只产生空记忆，不根据 runtime、catalog 或旧正文回填经历。v3 严格拒绝 bool/float/string schema version、extra 字段、非法或内容不匹配的派生 ID、孤立 scenario/fact 索引、不一致的顺序标记、重复记录、越界集合、float、set、异常、Pydantic 类型和其他非 JSON 值。序列化按稳定键和集合排序，可作确定性 MySQL JSON 往返。状态仍写入现有 `game_snapshots.state_json`；ORM 和 Alembic 无变化。

## 公开投影与未接线范围

`PlayerMemoryProjector` 先 JSON 往返隔离源状态，再输出 frozen tuple DTO。集合上限为 16 scenarios、32 NPCs、64 experiences、128 facts；总字符不超过 16,000，规范 UTF-8 JSON 不超过 32,000 bytes。超限时按可信 sequence 保留较新的记录并用 `truncated` 与总数明确标记，最终输出再按稳定 ID 排序。投影剥离 source event ID/sequence，且只含已被记忆边界确认的玩家已知引用；顶层公开事实项同时包含 scenario 和 fact 身份，不把裸 fact ID 当作跨副本全局身份。

Phase 2.3a 不接入 `NarrativePromptBuilder`、生产 `TurnOrchestrator`、Repository/UoW 或 API；不实现向量数据库、Embedding、RAG、记忆模型调用、前端、战斗或 `DeviationEvaluator`。生产接线、原子事件来源证明、何时触发各封闭记忆事件及长期压缩策略属于 Phase 2.3b 或后续独立阶段。

当前 NPC identity 也有意保持局部：同一 definition 跨 scenario 会形成不同 subject；scenario content version 改变时旧记录会冲突；本阶段不建立跨世界/跨版本人物身份。若未来内容允许 NPC 跨副本重现、同 definition 多实例或 scenario 重玩，必须先引入显式的稳定 run/subject identity，不能沿用当前键并默认为已支持。

Phase 2.3a 也不把 `ScenarioRuntimeState.dynamic_facts` 写入长期记忆；因此玩家/模型不能借 `dynamic.*` 自由键跨越 fact identity 与长度边界。FIXED/DEFERRED/MUTABLE 事实同样只保存引用，不保存可能过期的值；后续消费者若需要当前值，仍必须回到当前权威 scenario runtime/content，而不能把记忆引用解释成第二份当前真相。
