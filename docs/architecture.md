# 第一阶段架构边界

请求先进入 `ActionGateway`。它按 JSON 配置装配策略链，遇到拒绝或本地动作即停止，且保留截至该点的完整 `policy_trace`。只有通过全部本地规则的输入才得到 `NARRATIVE_NORMAL`。

`NARRATIVE_ANOMALY_CANDIDATE` 是应用层稳定路由值，但第一阶段不会自行提升任何输入。后续独立 `AnomalyEvaluator` 只能评估已经通过可行性和权限检查的合法行动，因此胡言乱语、不可实现动作和随机输入不会绕过本地闸门。

会话快照代表频繁变化的聚合状态，使用 MySQL JSON 保存；会话身份、阶段、回合号和 `state_version` 保留为关系列。领域事件提供审计与重建线索。Repository 在同一个 `AsyncSession` 中先执行带版本条件的会话更新，再写快照和事件，最终由 Unit of Work 统一提交。

第一阶段的回合处理在查询幂等记录前以 `SELECT ... FOR UPDATE` 锁定对应会话行，使同一会话的回合串行化；`turn_requests(session_id, client_request_id)` 唯一约束继续作为最终数据库防线。这样并发重试会在首个事务提交后读取已保存响应，不会再次进入业务处理。

剧情事实的责任边界由 `StoryMutationValidator` 固化。FIXED 不可写，DEFERRED 首次绑定后不可写，MUTABLE 和 `dynamic.*` 都需要真实 `causal_event_id`。

## Phase 1.1 角色与能力边界

`domain.content` 保存版本化静态定义与 `ContentCatalogLoader` 端口；静态定义只使用稳定 `definition_id` 互相引用。目录在成为可用对象前统一检查重复 ID、缺失引用、技能前置循环、不可达等级以及装备与物品定义的一致性。效果仅有受判别字段约束的结构化类型，倍率统一使用整数基点，不支持任意表达式或脚本。

`domain.state.GameState` 是写入 `game_snapshots.state_json` 的运行时聚合，显式携带快照 `schema_version` 和内容版本。`schema_version` 描述 JSON 结构兼容性，`content_version` 标识状态所引用的具体内容包，两者不能互换。玩家、NPC、物品实例、装备状态、技能状态、钱包与资源只保存会变化的数据；名称、上限、前置条件、装备需求与效果仍由 `ContentCatalog` 掌管。所有领域操作先验证完整前置条件，再改变聚合，失败使用稳定领域错误码且不留下部分修改。快照输出还会重新验证嵌套结构，阻止绕过聚合方法产生的非法状态进入持久化边界。

原有 `domain.models.Player`、`NPC` 和 `Inventory` 保留原构造语义，仅作为 Phase 1 兼容 DTO，不参与 `GameState` 或 Phase 1.1 规则。权威运行时模型是 `PlayerState`、`NpcState` 和 `InventoryState`；原有 `GameSession` 持久化聚合与 `Scene` 保持不变。

`AuthoritativeStateView` 为后续 `RuleResolver` 和行动上下文适配器提供脱离可变聚合的不可变投影。物品输入按 `item_instance_id` 检查，技能按 `skill_definition_id` 检查，NPC 按当前会话中的运行时 `npc_id` 检查；玩家叙述文本不是状态来源。状态改变后需要重新创建投影。当前尚未由 `FirstPhaseTurnOrchestrator` 自动构建该视图或全面接入 `ActionGateway`；现阶段只建立了查询接口，并通过策略链测试验证了手工投影后的衔接行为。

装备槽位同时受装备定义和玩家角色定义约束。同一实例只保存一个 `equipped_slot`，槽位占用不另建第二份记录。零耐久装备不能新装备；已装备物品在耐久降到零时不会被隐式卸下，必须显式卸下后才能移除。

JSON 内容包文件由 `infrastructure.content_loader` 以 UTF-8 读取并交给领域目录验证。领域层不知道文件路径，基础设施加载器也不改变运行时状态。Phase 1.1 继续复用现有 MySQL JSON 快照、Repository、UoW 和领域事件模型，不增加业务表。
