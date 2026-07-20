# Phase 2.4a 可玩垂直切片

## 已证明的公共路径

Phase 2.4a 只承诺以下路径能够由玩家通过公共 ASGI API 完成：

1. `POST /v1/sessions` 创建 `death_certificate` session。
2. `GET /v1/sessions/{session_id}/view` 取得开局已提交权威状态。
3. `POST /v1/sessions/{session_id}/actions` 提交合法开局 Narrative 行动。
4. Scripted Provider 候选经真实 validator、NarrativeOutcomePolicy、NarrativeEventIssuer 和 StoryDirector finalize。
5. view 显示 `death_certificate.life_disputed` 与 `stop_condition=CONTINUE`。
6. 玩家连续提交三个无载荷 CONTINUE；每个请求只推进一个 auto beat。
7. 第三个响应和后续 view 显示 `death_certificate.decision.early_strategy`、`AWAIT_PLAYER`。

真实生产可达性由 MySQL 上的完整公共 ASGI API 路径证明：它使用生产 Repository 连续完成三个 CONTINUE 并到达首个后续决策。无数据库内存 adapter 仅保留为快速 Repository contract/playtest，不作为唯一 PLAY-001 证明。两条测试都不通过私有 scenario event issuer、`StoryDirector.advance_after_verified_result`、Repository 内部写方法或测试专属状态入口推进剧情。Scripted Provider 不访问网络；整个路径 Provider 调用一次，CONTINUE 期间为零次。

## CONTINUE 合同

请求体仍使用统一 action endpoint：

```json
{
  "turn_id": "continue-turn-1",
  "client_request_id": "continue-request-1",
  "action_type": "CONTINUE"
}
```

除上述三个公共字段外，CONTINUE 不接受 description、dialogue、target/tool、decision/choice、item/equipment/skill 或 extra 字段；这些非法 HTTP 请求在创建 turn request 或进入 orchestration 前统一返回 422。ActionGateway 与 ContinueInputPolicy 仍作为非 HTTP 调用的独立防线。服务器只在重新锁定并加载后确认 scenario ACTIVE、Frame 为 CONTINUE 且无 decision 时推进。成功响应为本地权威回合，不含文学正文；返回的新 Frame 告诉客户端继续提交 CONTINUE，或在 AWAIT_PLAYER 时提交实际玩家选择/行动。

同一 `client_request_id` 必须携带同一 turn 和完整语义。相同请求重放或并发到达时返回首次持久化响应，不推进第二次；复用 ID 提交不同语义返回幂等冲突。

## 断线恢复

`GET /v1/sessions/{session_id}/view` 返回：

- session metadata 与 state version；
- 从最新已提交 snapshot 重新规划的安全 Frame；
- 玩家公开状态和长期记忆投影；
- ACTIVE/ENDED 与公开 clock；
- 最多 6 条、合计最多 12,000 字符和 24,000 UTF-8 bytes 的 COMMITTED 近期正文；
- 仅在 ENDED 时出现的 ending ID。

view 不返回 snapshot、GameState、ScenarioDefinition、隐藏事实、未发现线索、NPC 秘密、未来 ending、内部 rule/signature/fingerprint、job/lease/token、proposal、Provider metadata、event sequence 或 memory 内部同步细节。Narrative pending 时 view 仍显示最后已提交状态。

`GET /v1/sessions/{session_id}/requests/{client_request_id}` 用于恢复 Narrative 请求：

| 状态 | 客户端动作 |
|---|---|
| `PENDING` | 以同一 request ID 轮询；遵守固定 `Retry-After: 2` |
| `COMMITTED` | 使用返回的已持久化公共 TurnResponse |
| `STALE` | 先刷新 view，再决定是否用新 request ID 提交 |
| `OUTCOME_UNKNOWN` | 禁止自动重发；等待人工/产品策略 |
| `FAILED` | 终止错误，不自动重发 |

内部遗留 `FAILED_RETRYABLE` 记录也映射为 `FAILED/DO_NOT_RETRY`。当前生产代码没有转换到 FAILED_RETRYABLE 的路径，公共 schema 不宣称支持 RETRY_WITH_NEW_REQUEST。

查询是只读操作，不 claim lease、不调用 Provider。不存在和非 owner session 都遵守安全 ownership 404。

## 尚未完成

Phase 2.4a 不保证 `early_strategy` 之后的 investigation 线索生产路径、disposal escape、self-fulfilling truth、core conflict、正式 ending 或 deadline failure ending。结构化内容中存在这些节点只说明领域定义和静态图存在；让它们通过公共生产协议完整可玩属于 Phase 2.4b。
