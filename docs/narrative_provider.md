# NarrativeProvider 边界（Phase 2.2b-1）

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

配置仅在显式调用 `DeepSeekSettings.from_environment()` 时读取进程环境；模块导入不会读取 key、创建 client 或联网。默认 timeout 30 秒、max output 1,200 tokens、最多 2 次 retry（总共最多 3 次尝试），且配置模型进一步限制 timeout、token 与 retry 上界。玩家请求无法覆盖这些值。

错误映射与重试：

- 400/422：请求参数错误，不重试。
- 401：认证失败，不重试。
- 402：余额不足，不重试。
- 429、500、503：有界指数退避。
- 连接失败和 timeout：有界指数退避。
- 空 content 或 JSON 解析失败：最多一次受控重试，并受总尝试数限制。
- `finish_reason=length`：截断失败，不接受局部 JSON。
- 其他状态、finish reason 或响应形状：固定 provider 失败。

等待器与传输均可注入，离线测试不会真实 sleep 或访问网络。错误字符串、repr、日志与 DTO 不包含 API key、Authorization、完整 prompt、完整原始 response 或供应商异常文本。

## 可选 live smoke

默认 `pytest` 不访问网络。测试只有在进程环境同时满足 `DEEPSEEK_API_KEY` 存在且 `RUN_LIVE_DEEPSEEK_TEST=1` 时才运行；仅存在 key 仍会 skip。smoke 固定 `deepseek-v4-flash`、thinking disabled、non-stream、较小 token 上限、0 retry，只发送一次微型玩家安全 Frame，不创建 engine、不连接 MySQL，并要求响应通过 `NarrativeProposalValidator`。

```powershell
$env:RUN_LIVE_DEEPSEEK_TEST = "1"
.\.venv\Scripts\python.exe -m pytest tests\live\test_deepseek_live.py -m live -s
```

成功时只允许显示安全 `narrative_text`、model 和 usage；失败只报告稳定错误码。Phase 2.2c 之前，这条 smoke 路径不会被生产 orchestrator 或 API 调用。
