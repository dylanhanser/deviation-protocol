# Phase 2.4b 可玩垂直切片

## 已证明的公共路径

`死亡证明已签发` 的 content version 为 `death-certificate-1.1.0`。Phase 2.4b 通过公共 ASGI API 和无网络 Scripted Provider 证明两条完整路径：

- 成功路径：创建 session，完成开局生命信号、临床复核和 NPC 存活确认，经单 beat `CONTINUE` 与公开 choice 进入 disposal escape；随后由公开调查 choice 开放档案室，再用当前位置内的普通 `EXPLORE`/`OBSERVE` 行动取得三个调查线索组的必要线索并开放地点，经过 self-fulfilling truth，在 core conflict 连续完成四个 rapid decision window，最终由 `core.conflict.resolved` 进入 `death_certificate.ending.protocol_broken` 或 `death_certificate.ending.record_challenged`。
- 截止失败路径：创建独立 session，以公开 `CONTINUE`、choice 和安全 no-effect Narrative 行动真实消耗 `predicted_death_deadline`，从 0 到 13 后由 `deadline.reached` 进入 `death_certificate.ending.deadline_reached`。

两条路径都从 `POST /v1/sessions` 开始，只经 `/actions`、`/view` 和 `/requests/{client_request_id}`。测试不直接调用 StoryDirector、私有 issuer、Repository 状态写方法，也不修改 snapshot、runtime 或 clock。成功路径和代表性失败、rollback、duplicate 场景还经过生产 SQLAlchemy Repository 与真实 MySQL；测试结束后五张业务表无残留。

## 生产 outcome 路径

服务器目录定义封闭 outcome templates，Provider 只能从本回合 opaque token 与允许的结果类型中选择：

- `life_disputed_clinical_recheck`：普通 TALK/CUSTOM/OBSERVE/EXPLORE 的连贯生命信号可触发 `clinical.reviewed`，固定目标分诊协调员必须给出支持存活与生命体征的可见台词；可信结果补足生命线索，NPC 记忆只由对应持久化事件规则生成。
- 首个调查公开 choice：固定服务器事件开放并进入 records room；choice 只证明玩家选择，地点效果来自声明式 action template。
- `investigation_records_route`：在 records room 使用普通 `EXPLORE`/`OBSERVE` 得到 `record_timestamp` 与 `protocol_feedback`。
- `investigation_audit_route`：仍在 records room 使用普通 `EXPLORE`/`OBSERVE` 得到 `audit_sequence` 与 `comparison_case`，开放并进入 observation level。
- `investigation_patient_route`：在 observation level 使用普通 `EXPLORE`/`OBSERVE` 得到 `patient_vitals` 与 `monitor_history`，并开放 control room；固定目标 NPC 必须在当前 Frame 可见，但其台词不构成线索权限。

自由文本语义、隐藏答案、职业知识和精确措辞都不是线索授权条件。即使玩家用行动句式直接猜中三个隐藏结论，只要尚未经过公开 decision 和正确当前位置，服务器仍只提交固定 no-effect 文本，不授予线索或地点。所有 production outcome 的公开正文均来自固定服务器模板，Provider 的矛盾措辞不会进入响应。
- 每个允许自由 Narrative 行动的可访问阶段都有服务器定义的 no-effect fallback。fallback 只消耗该阶段声明的时间成本，不发现线索、不开放地点、不产生核心事件或 ending。

玩家文本直接猜中隐藏事实不会获得线索。模型正文、`continuity_notes` 和 proposal references 不能提供 fact/clue/event payload、NPC authority、location、clock delta、ending 或 memory operation。MOVE 和 CONTINUE 仍走本地确定性路径。

## 节奏、决策与截止

`CONTINUE` 仍是无载荷协议，每次只调用 Director 一次且不调用 Provider。前期决策保持稀疏：开局立即窗口之后，`life_disputed` 经连续 beats 才开放 `early_strategy`；investigation 只在已声明窗口暂停。core conflict 使用四个相邻 rapid windows。每次 CHOOSE 必须提交当前 Frame 绑定的 public decision token 和 choice ID；旧 token 稳定拒绝且不改变状态。

Choice 只证明玩家选择。最终 choice 的世界效果来自目录中固定的 `server_event_type=core.conflict.resolved` 和允许的 mutable fact transition，不能从玩家或模型正文推断。目录校验要求该事件属于已声明 mutable transition，固定 fact update 也必须匹配同一事件和值。

`predicted_death_deadline` 是唯一实时截止权威。合法 auto beat、阶段 action cost 和 no-effect outcome 从 0 真实推进到 13；不允许正文自报时间或客户端 delta。达到阈值后返回 SETTLEMENT/SCENARIO_ENDED，后续 CONTINUE、CHOOSE 与 Narrative mutation 都稳定拒绝并保持版本不变。

## 原子结算与恢复

成功与失败 ending 都来自 StoryDirector 生成的可信事件。结束候选只允许在同一 resolution 已包含与 ending 精确匹配的声明式 COMPLETE_SCENARIO rule 时通过受限预检；预检只临时投影唯一 scenario record 的完成字段并重新运行完整验证。事件 insert/flush 后，memory rule 把真实 ScenarioMemoryRecord 标记为 COMPLETED，随后仍执行最终完整 snapshot/catalog/memory 验证。ending、memory、event、snapshot、TurnResponse、job 和 session version 共享一个 UoW commit，任何失败全部 rollback。Narrative action 提交通常的 Provider job；最终本地 CHOOSE 提交 attempt=0 的 `local-server-template-v1` job，正文只来自可信 decision template且不调用 Provider。

`GET /v1/sessions/{session_id}/view` 在活动期恢复当前安全 Frame，在结束后稳定返回 settlement、ending 与完成记忆。`GET /requests/{client_request_id}` 可恢复 COMMITTED Narrative response；查询、拒绝和重复请求不推进 beat、clock、event 或 version。

公开响应不包含隐藏事实、隐藏 clock、未来 ending、rule ID、outcome token 内部结构、lease、receipt、Provider metadata 或 snapshot。Scripted playtest 对每次 prompt 同时验证 32,000 字符与 64,000 UTF-8 bytes 上限。默认与正常验证不调用 live DeepSeek。

## 本阶段之外

Phase 2.4b 不包含 Web 前端、scenario replay/`scenario_run_id`、跨 scenario NPC identity、memory rebuild/compaction、DeviationEvaluator、高维异常、战斗、worker/queue/distributed system、RAG 或 vector database。
