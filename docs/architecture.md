# 第一阶段架构边界

请求先进入 `ActionGateway`。它按 JSON 配置装配策略链，遇到拒绝或本地动作即停止，且保留截至该点的完整 `policy_trace`。只有通过全部本地规则的输入才得到 `NARRATIVE_NORMAL`。

Phase 1.2 的确定性链路为：

```text
PlayerAction
  -> AuthoritativeStateView
  -> AuthoritativeActionContextFactory
  -> TrustedResolutionContext(ActionContext)
  -> DeterministicRuleResolver
       -> ActionGateway（内部强制执行）
  -> ResolutionResult
  -> 候选 GameState + DomainEventDraft + NarrativeFact + PlayerFeedback
```

`AuthoritativeActionContextFactory` 校验传入视图确实来自同一 `GameState` 与 `ContentCatalog`，然后分别投影 `item_instance_id -> item_definition_id`、`item_instance_id -> equipment_definition_id`、`skill_definition_id -> level` 和 `npc_id -> npc_definition_id`。场景可见性仍由 application 层显式传入，因为当前 `GameState` 不建模场景；缺省可见/可交互集合为空，玩家文本不会自动把 target/tool 加入权威集合。静态 definition ID 不能冒充物品、环境工具或 NPC 的 runtime ID。每次状态改变后必须重新构造视图和上下文。普通 `ActionContext` 是不可变投影但不是结算授权；只有工厂签发且绑定当前 state/catalog 摘要的 `TrustedResolutionContext` 能进入 resolver。

`ActionGateway` 是行动资格和路由边界。它拒绝陈旧回合、重复请求、错误字段组合、不可见目标、非本人持有的实例、未知技能引用、胡言乱语、越权叙述、NPC 控制、系统奖励命令和多主行动。`RuleResolver.resolve` 不接受调用方传入 route 或 `GatewayResult`，而是从密封上下文内部调用真实 gateway 后执行更具体的领域规则；因此手工构造 `RESOLVE_LOCAL` 或异常 route 不能进入结算。网关拒绝不会成为叙事或异常候选。

## Phase 1.2 本地结算与叙事边界

以下操作返回 `RESOLVED_LOCAL`：状态、库存、装备、技能、资源、货币和任务占位查询；装备与卸下；使用内容标签明确允许的消费品；在权威可学习机会中学习技能；升级已学习技能；使用已学习的结构化技能。查询不改变状态，也不调用 `NarrativeProvider`；尚未建模的任务查询明确返回空列表，不伪造任务。

技能结算检查技能是否已学习、等级和前置、资源成本、现有 `cooldown_remaining` 以及当前是否要求尚未建模的目标。成功时成本、所有效果和 `uses` 计数一起提交为候选状态；任何一步失败都不扣资源、不改变次数、不产生成功事件。当前内容没有冷却时长或每级学习成本定义，因此解析器只严格执行已存在的冷却状态，不能自行发明数值。

消费品按真实 `item_instance_id` 读取。普通堆叠物品每次减少一个数量，带 charge 的消费品每次减少一次 charge，并在最后一次使用后移除实例；已装备实例、非消费品、未知实例或不足 charge 都会失败且不改变原状态。装备仍由 `GameState.equip` 检查定义存在、槽位、角色槽位、属性/技能要求、占用和耐久。

`DeterministicEffectExecutor` 只支持内容模型已经判别、且与已验证 `ContentCatalog` 中对象完全一致的 `ATTRIBUTE_MODIFIER` 与 `RESOURCE_MODIFIER`；调用方自建或改写的 effect 会失败。属性倍率使用整数基点和整数除法，结果受非负 64 位整数技术边界约束；资源负 delta 表示消耗，正 delta 表示恢复，并走 `GameState` 校验。执行顺序必须是内容定义中的显式稳定序列。当前 `ATTRIBUTE_MODIFIER` 仅表示由 `SYSTEM_RULE` 或 `REWARD_SETTLEMENT` 产生的永久基础属性变化，事件明确记录 `modifier_scope=PERMANENT`；技能与装备不得借此永久叠加临时加成，装备派生值和战斗临时效果尚未实现。缺失、被改写、语义不支持或类型不支持的 effect 都会明确失败。执行器不使用 `eval`、`exec`、动态导入、脚本或全局随机数。

开放式探索、观察、移动、对话、选择和特殊尝试返回 `NARRATIVE_REQUIRED`。结果只携带标记为 `VALIDATED_INTENT` 的玩家意图和标记为 `AUTHORITATIVE_CONTEXT` 的已验证 instance/runtime ID 映射，不把意图伪装成已发生结果、不写永久状态、不认定行动“独特”，也不触发 NPC 异常或场景崩坏。`ANOMALY_EVALUATION_REQUIRED` 是未来真实 gateway/anomaly evaluator 的预留状态；Phase 1.2 不包含 `DeviationEvaluator`，调用方不能向 resolver 传入该 route，resolver 也从不自行提升行动。

玩家协议没有 grant item/skill、增加货币/资源、改属性、改 NPC、伪造已验证事实/网关 route 或生成实例的字段。自然语言中的此类系统命令由独立 `SystemAuthorityPolicy` 拒绝。合法系统奖励和资源变化只能由授权规则/剧情事件直接调用领域方法或结构化效果执行器。技能学习授权不在 `PlayerAction` 或普通 `ActionContext` 中：应用层必须从 `PERSISTED_FACT`、`REWARD_SETTLEMENT` 或 `SYSTEM_RULE` 签发不可由请求 JSON 重建的 `SkillLearningAuthorization`，其来源和 source ID 会进入成功事件。未来编排器负责保证该 source ID 确实对应已持久化事实或已完成结算。

## 原子性、事件和事务

每次突变先由 `GameState.to_snapshot()` / `from_snapshot()` 创建并验证候选副本。技能成本先写候选，效果执行器再克隆该候选；嵌套字典、集合、物品、装备、技能和资源对象均不与原聚合共享可变引用。只有全部效果和最终 catalog 校验成功，`ResolutionResult.updated_state` 才存在。失败结果没有新状态、成功事件或叙事事实，因此调用方不可能误提交部分变化。

`DomainEventDraft` 表示已经在成功候选状态中发生、但尚未包裹持久化元数据的结构化事件；事务编排器负责注入 `event_id`、`sequence_no`、`occurred_at`、会话和回合后生成现有 `DomainEvent`。`NarrativeFact` 以 kind 区分已验证意图、权威上下文、查询结果和已发生状态，且不是 `StoryFact` 真相突变；`PlayerFeedback` 仅含稳定代码和安全参数。三者的 JSON 值在构造时深度复制、校验并冻结，`ResolutionResult` 还执行成功/拒绝/叙事的跨字段约束。`RuleResolver` 不访问 Repository、不提交 UoW、不生成数据库序号/时间/随机 UUID，也不负责 `client_request_id` 幂等或最终文学文本。

`NARRATIVE_ANOMALY_CANDIDATE` 是应用层稳定路由值，但第一阶段不会自行提升任何输入。后续独立 `AnomalyEvaluator` 只能评估已经通过可行性和权限检查的合法行动，因此胡言乱语、不可实现动作和随机输入不会绕过本地闸门。

会话快照代表频繁变化的聚合状态，使用 MySQL JSON 保存；会话身份、阶段、回合号和 `state_version` 保留为关系列。领域事件提供审计与重建线索。Repository 在同一个 `AsyncSession` 中先执行带版本条件的会话更新，再写快照和事件，最终由 Unit of Work 统一提交。

第一阶段的回合处理在查询幂等记录前以 `SELECT ... FOR UPDATE` 锁定对应会话行，使同一会话的回合串行化；`turn_requests(session_id, client_request_id)` 唯一约束继续作为最终数据库防线。这样并发重试会在首个事务提交后读取已保存响应，不会再次进入业务处理。

剧情事实的责任边界由 `StoryMutationValidator` 固化。FIXED 不可写，DEFERRED 首次绑定后不可写，MUTABLE 和 `dynamic.*` 都需要真实 `causal_event_id`。

## Phase 1.1 角色与能力边界

`domain.content` 保存版本化静态定义与 `ContentCatalogLoader` 端口；静态定义只使用稳定 `definition_id` 互相引用。目录在成为可用对象前统一检查重复 ID、缺失引用、技能前置循环、不可达等级以及装备与物品定义的一致性。效果仅有受判别字段约束的结构化类型，倍率统一使用整数基点，不支持任意表达式或脚本。

`domain.state.GameState` 是写入 `game_snapshots.state_json` 的运行时聚合，显式携带快照 `schema_version` 和内容版本。`schema_version` 描述 JSON 结构兼容性，`content_version` 标识状态所引用的具体内容包，两者不能互换。玩家、NPC、物品实例、装备状态、技能状态、钱包与资源只保存会变化的数据；名称、上限、前置条件、装备需求与效果仍由 `ContentCatalog` 掌管。所有领域操作先验证完整前置条件，再改变聚合，失败使用稳定领域错误码且不留下部分修改。快照输出还会重新验证嵌套结构，阻止绕过聚合方法产生的非法状态进入持久化边界。

原有 `domain.models.Player`、`NPC` 和 `Inventory` 保留原构造语义，仅作为 Phase 1 兼容 DTO，不参与 `GameState` 或 Phase 1.1 规则。权威运行时模型是 `PlayerState`、`NpcState` 和 `InventoryState`；原有 `GameSession` 持久化聚合与 `Scene` 保持不变。

`AuthoritativeStateView` 为 `RuleResolver` 和行动上下文适配器提供脱离可变聚合的不可变投影。物品输入按 `item_instance_id` 检查，技能按 `skill_definition_id` 检查，NPC 按当前会话中的运行时 `npc_id` 检查；玩家叙述文本不是状态来源。状态改变后需要重新创建投影。Phase 1.2 已由 `AuthoritativeActionContextFactory` 自动完成投影和一致性校验；resolver 使用 `create_trusted` 的结果，普通 gateway-only 场景可使用 `create`。`FirstPhaseTurnOrchestrator` 尚未扩展为完整结算编排器，本阶段没有加入数据库快照/内容包加载和 draft event 封装流程。

装备槽位同时受装备定义和玩家角色定义约束。同一实例只保存一个 `equipped_slot`，槽位占用不另建第二份记录。零耐久装备不能新装备；已装备物品在耐久降到零时不会被隐式卸下，必须显式卸下后才能移除。

JSON 内容包文件由 `infrastructure.content_loader` 以 UTF-8 读取并交给领域目录验证。领域层不知道文件路径，基础设施加载器也不改变运行时状态。Phase 1.1 继续复用现有 MySQL JSON 快照、Repository、UoW 和领域事件模型，不增加业务表。
