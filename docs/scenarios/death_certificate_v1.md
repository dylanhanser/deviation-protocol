# 《死亡证明已签发》v1 结构化副本规格

当前生产 content version 为 `death-certificate-1.1.0`。版本 1.1 补齐公共 API 的完整可达 outcome 路径，不改变核心真相或七阶段结构。

## 内容与版权边界

本规格及 `config/scenarios/death_certificate_v1.json` 是原创副本设计，只描述机器可读的事实、规则和短标签。它不包含参考小说原文、人物、世界观、剧情、怪物、装备、技能、专有名词、系统提示、备注或笑话，也不提供最终文学叙事。未来叙事提供者只能根据安全 `NarrativeFrame` 渲染原创文本。

## 核心命题

一份提前生效的死亡记录触发处置规程；规程正在制造记录所预测的结果。玩家需要证明自己仍然存活，核对签发与诊断的时间次序，发现另一名仍存活的观察对象，并在最后冲突中处理处置规程与证据去向。

固定事实不会因玩家或叙事输出改变。审计入口是从有限候选首次绑定的 Deferred 事实；处置规程和安保姿态是带显式事件转换的 Mutable 事实。玩家形成的新路线或计划只能写入受限 `dynamic.*` 命名空间。

## 开场事实与公开目标

内容包共声明 15 个事实。开场新增的 5 个 `FIXED`、`PLAYER_KNOWN` 结构化事实与既有事实共同表达以下状态，不依赖文学提示字符串：

- `opening_body_bag_state`：玩家恢复意识时已在尸袋内部，拉链处于闭合进行中。
- `opening_time_conflict`：历史开场时点为 02:18（午夜后 138 分钟），已签发记录中的死亡时间为 02:31（午夜后 151 分钟），两者相差 13 分钟；同一值还引用唯一的 `predicted_death_deadline` 时钟及其 0 到 13 的边界。
- `death_certificate_issued`：死亡证明已经签发。
- `comfort_disposition_imminent`：注射或舒适处置流程即将执行。
- `initial_survival_objective`：在 02:31 前，至少一名存在于运行时 `GameState.npcs` 的真实 NPC 明确承认玩家仍然活着。

既有 `record_marks_player_dead` 表达记录已将玩家标记死亡；`record_predates_diagnosis` 仍是需要线索支持后才能公开的独立固定真相，不能替代 02:18 与 02:31 的 13 分钟冲突。历史时点和记录时间只由固定事实持有，不能被后续推进修改；实时剩余预算只由 `predicted_death_deadline` 持有，不建立第二套通用时间状态。

开局只有 `immediate_survival` 一个必要决策窗口。四条结构化建议分别是有规律地移动仍可控制的手指、干扰指夹式血氧传感器、调整呼吸制造可识别生命信号、保持安静并获取现场信息；受约束自定义行动仍然开放，建议不预写成功结果，也不限制玩家只能选择这些动作。

## 阶段与节奏

副本包含七个必要阶段：

1. `death_certificate.arrival_locked`：开场唯一一次立即生存决策。
2. `death_certificate.life_disputed`：至少三个连续 beat 后才开放一次早期策略决策。
3. `death_certificate.disposal_escape`：沿已建立的脱离路线自动推进，不因普通移动停顿。
4. `death_certificate.investigation`：以 beat 1、4、8 附近的三个窗口实现低频调查决策；达到证据目标可提前转场。
5. `death_certificate.self_fulfilling_truth`：用已完成线索组呈现因果关系并连续推进。
6. `death_certificate.core_conflict`：进入 rapid 模式，最多四个相邻的关键决策窗口。
7. `death_certificate.resolution`：结构化结算，不强制额外选择。

转场由事实、线索组、已验证事件、时钟和决策响应等声明式条件决定，不写死唯一行动线路。

## 线索、职业与知识边界

四个线索组分别是 `player_is_alive`、`death_record_predates_diagnosis`、`prediction_causes_outcome` 与 `underground_patient_alive`。每组为三条线索中满足两条，其中至少两条不要求职业标签；职业只能提供替代路径，不会成为通关硬门槛。

生产模板为后三组各提供两条无职业门槛的必要线索。首个公开调查 choice 以固定服务器事件开放并进入 records room；当前位置内的机械 `EXPLORE`/`OBSERVE` 随后依次产生 `record_timestamp` 与 `protocol_feedback`、`audit_sequence` 与 `comparison_case`、`patient_vitals` 与 `monitor_history`。审计结果进入 observation level，患者结果开放 control room。授权不依赖隐藏口令、精确句式或文本语义；玩家直接说出隐藏答案不会生成线索，no-effect fallback 也不会开放地点。所有公开 outcome 正文来自固定服务器模板。

可用标签为 `CLINICAL_LITERACY`、`SYSTEMS_REASONING`、`DOCUMENT_AUTHORITY`、`EVIDENCE_CHAIN`、`PHYSICAL_RESPONSE` 与 `DEESCALATION`。它们只影响额外信息、线索路线或合法建议动作，不决定玩家性格、不赠送物品或技能、也不保证成功。

玩家只会在公开事实或支持线索已发现后看到真相。分诊协调员、档案保管员和地下观察对象各自只有明确列出的事实知识；`NarrativeFrame` 只为 `GameState.npcs` 中真实存在且当前位置可见的运行时 NPC 建立分区，并只携带其权限范围与玩家当前知识的安全交集，不能把 NPC 秘密或一个 NPC 的知识提供给另一个 NPC。

## 威胁时钟与结局

`disposal_protocol`、`predicted_death_deadline`、`security_alert` 和 `underground_patient_stability` 都是有界整数时钟。只有自动 beat 或阶段声明的行动成本推进它们，阈值产生稳定事件；文本声明时间流逝没有状态权限。公开程度由各时钟定义控制。`predicted_death_deadline` 从 0 开始、在 13 达到截止阈值，每一单位表示自 02:18 起消耗的一分钟预算；02:18 与02:31本身仍是不可修改的历史记录事实。

核心冲突连续开放四个 rapid decision windows。每个选择仍必须使用当前 public Frame 的绑定 token 与 choice ID；最终正式行动由服务器目录固定生成 `core.conflict.resolved`，`final_suspend` 同时按已声明 mutable transition 将 `disposal_protocol_active` 置为 false。玩家 choice 或正文不能自带世界效果。

结局由声明条件评估，包括服务器记录的具体 runtime NPC 存活承认证据、`player_is_alive` 与三个调查线索组、暂停/公开处置规程、核心冲突完成或截止时钟达到上限。公共成功路径可进入 `protocol_broken` 或 `record_challenged` RESOLVED ending；公开耗时行动把 deadline 从 0 推进到 13 时，阈值事件进入 `deadline_reached` FAILED ending。三者都由可信持久化事件触发精确匹配的 `COMPLETE_SCENARIO` memory rule，ScenarioMemoryRecord、ending、event、snapshot、response、job 和 version 原子提交。成功 ending 的最后一步是本地确定性 CHOOSE：固定结算正文来自服务器 decision template，并写入 attempt=0 的 `local-server-template-v1` COMMITTED job；不调用 Provider。
