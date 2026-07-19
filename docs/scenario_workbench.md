# Scenario Workbench 第一阶段

Scenario Workbench 是完全本地、只读、确定性的副本内容检查工具。它复用正式 `JsonScenarioCatalogLoader`、`ScenarioCatalog`、`ContentCatalog`、`GameState` 和 `DeterministicStoryDirector`；不读取 `.env`，不连接数据库，不调用 NarrativeProvider，也不发送网络请求。

## 命令

在 PowerShell 7+ 中使用仓库 `.venv`：

```powershell
.\.venv\Scripts\python.exe -m deviation_protocol.tools.scenario validate config/scenarios/death_certificate_v1.json
.\.venv\Scripts\python.exe -m deviation_protocol.tools.scenario analyze config/scenarios/death_certificate_v1.json
.\.venv\Scripts\python.exe -m deviation_protocol.tools.scenario preview config/scenarios/death_certificate_v1.json --character-id character.death_certificate.investigator
```

三个命令都支持：

```text
--content-pack <path>
--character-id <id>
--json
```

场景包内嵌的正式 `content_catalog` 是默认内容目录，因此默认行为不依赖当前工作目录。`--content-pack` 可显式替换它，但外部目录必须通过现有严格 ContentCatalog loader，并与场景 content version、NPC、物品、职业标签等引用完全匹配。

`preview` 必须显式提供一个真实、可玩的 `--character-id`，不会猜测角色或职业标签。`analyze` 可不提供角色；此时结构分析仍会执行，但初始公开 Frame 的预算明确标记为 unavailable。提供真实角色后，analyze 会附带初始 Frame 预算。

`--json` 使用排序键和稳定紧凑编码，相同输入会产生字节级相同输出，可作为未来 CI 的机器接口。退出码为：

- `0`：成功，且没有阻断级分析诊断。
- `1`：命令、文件、JSON、严格目录验证或参数错误。
- `2`：内容已成功加载，但静态分析发现阻断级问题。

错误输出使用稳定错误码，不包含 traceback、绝对本地路径、环境变量值、密钥或数据库 URL。

## validate

`validate` 直接通过现有严格 loader 和 `ScenarioCatalog`，不会在 CLI 中维护第二套验证器。它覆盖现有模型已经实施的 JSON/重复 key、schema/content version、额外字段、ID 与交叉引用、必要阶段可达性、自动循环上界、事实变化、decision cadence、outcome effect 边界，以及文件大小、嵌套、集合和字符串限制。正式目录验证成功后还会运行有界静态分析；若存在阻断级诊断，输出验证摘要并退出 `2`，不会以成功退出码掩盖 analyzer 的错误。

成功摘要只包含 scenario/version、初始 phase/location、结构计数和诊断计数；不输出隐藏事实值、NPC 秘密、结局条件、outcome token 或规则模板。

## analyze

`analyze` 在已验证的 `ScenarioDefinition` 上运行纯 application 分析，提供：

- 从 initial phase 开始的结构可达性、稳定 transition 顺序、死端、强连通循环和自动循环边界。
- ending 的 `structurally_referenced`、`source_phase_reachable`、`condition_satisfiable_unknown` 和 `guaranteed_reachable` 四层结论；条件无法静态证明时保持 `unknown`。
- 每个 phase 的 decision window、rapid 标记、auto beat 范围、重复窗口和选择密度信号。
- clue 可见性分类、N/M clue group，以及 `has_declared_source`、`source_structurally_reachable`、`source_condition_satisfiable_unknown`、`guaranteed_discoverable` 四层 producer 结论。
- FIXED/DEFERRED/MUTABLE/DYNAMIC 统计，以及当前 outcome templates 中未声明绑定或更新的事实。
- clock 边界、阈值、可见性、声明式 action/auto advance 范围，并区分声明了推进源、来源结构可达、推进条件未知与保证推进；无来源和可能重复预算仅作准确或保守提示。
- 初始公开 Frame 的稳定 JSON 字符数、UTF-8 字节数、列表、事实、NPC、线索、时钟和建议动作计数。

token 估计仅是 `UTF-8 bytes / 4` 的粗略 heuristic，不是 DeepSeek tokenizer 或计费结果。

### 静态分析边界

图可达只证明 transition 图上存在结构路径，不证明所有运行时条件能同时满足。事件、玩家选择、条件组合、外部可信 resolver 结果和未来内容扩展通常只能标记为 `unknown`。工具不进行完整路径穷举或随机模拟。

`has_declared_source` 表示当前声明式 outcome template 存在与 clue source event 匹配的发现 producer；`source_structurally_reachable` 还要求 producer phase 与 clue allowed phase 在结构上可达。`source_condition_satisfiable_unknown` 只排除可由固定事实、决策窗口或可见 NPC 声明静态证明不可能的来源。即使前三者显示存在潜在来源，工具仍把 `guaranteed_discoverable` 保持为 `unknown`，因为无法证明玩家一定选择或获得该结果。重复 producer 不会增加 N/M clue group 的线索数量，运行时重复发现仍由正式幂等规则处理。

decision cadence 信号是通用 heuristic，不替代正式 `DecisionCadencePolicy`。当前集中阈值为：每个窗口覆盖至少 3 个 beat 时分类为 sparse；连续至少 4 个无选择 beat 提示长间隔；每 2 个 beat 至少 1 个窗口作为高密度信号。rapid 与普通 phase 使用同一密度定义。所有这类诊断的代码以 `_HEURISTIC` 结尾、metadata 含 `heuristic=true`，且只产生 warning，不会成为 blocking error。

warning 表示可疑或需要作者复核但不阻断；error 表示已加载内容中的阻断级结构问题；info 记录能力边界或成功事实。诊断按 severity、code、subject 稳定排序，并设有总量上限。

## preview

`preview` 使用真实 ContentCatalog 角色构造临时 `GameState`，调用与生产 `SessionService` 共用的 NPC/runtime 初始化函数，再调用正式 StoryDirector 生成 initial Frame。它不会绕过 ScenarioRuntime，也不会手工从隐藏定义拼装 Frame。

输出只包含公开位置、玩家已知事实、可见 runtime NPC、公开 clock、公开 decision binding、建议动作、Frame ID 和预算。内部 decision definition ID、隐藏事实/NPC/clock、未来 ending、outcome token/rule、capability 和 seal 均不输出。生成结果与临时可变 GameState 深度隔离。

preview 使用固定的本地 synthetic session/player 标识，并在报告中标记 `LOCAL_SYNTHETIC_PREVIEW` 与 `LOCAL_PREVIEW_ONLY`。其中的 decision binding 只是可重复的展示结果，不是 capability、token、生产 API 凭证，也不能提交给真实 session；生产端会按真实 session ID、state version、scenario/version 重新绑定并拒绝该值。

## 不包含的能力

第一阶段不包含 `scenario new`、内容生成器、自动修复、文件改写、GUI、HTML 报告、后台服务、数据库读取、模型质量评价、Provider/DeepSeek 调用、战斗、异常、完整路径穷举、随机模拟或 Token 计费请求。
