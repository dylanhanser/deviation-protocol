# 第一阶段架构边界

请求先进入 `ActionGateway`。它按 JSON 配置装配策略链，遇到拒绝或本地动作即停止，且保留截至该点的完整 `policy_trace`。只有通过全部本地规则的输入才得到 `NARRATIVE_NORMAL`。

`NARRATIVE_ANOMALY_CANDIDATE` 是应用层稳定路由值，但第一阶段不会自行提升任何输入。后续独立 `AnomalyEvaluator` 只能评估已经通过可行性和权限检查的合法行动，因此胡言乱语、不可实现动作和随机输入不会绕过本地闸门。

会话快照代表频繁变化的聚合状态，使用 MySQL JSON 保存；会话身份、阶段、回合号和 `state_version` 保留为关系列。领域事件提供审计与重建线索。Repository 在同一个 `AsyncSession` 中先执行带版本条件的会话更新，再写快照和事件，最终由 Unit of Work 统一提交。

第一阶段的回合处理在查询幂等记录前以 `SELECT ... FOR UPDATE` 锁定对应会话行，使同一会话的回合串行化；`turn_requests(session_id, client_request_id)` 唯一约束继续作为最终数据库防线。这样并发重试会在首个事务提交后读取已保存响应，不会再次进入业务处理。

剧情事实的责任边界由 `StoryMutationValidator` 固化。FIXED 不可写，DEFERRED 首次绑定后不可写，MUTABLE 和 `dynamic.*` 都需要真实 `causal_event_id`。
