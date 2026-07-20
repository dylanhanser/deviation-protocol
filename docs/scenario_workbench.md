# Scenario Workbench

Scenario Workbench 是完全本地、确定性的副本内容工具。第一阶段的检查命令保持只读；第二阶段增加安全、确定性且不覆盖现有内容的 `scenario new` 草案脚手架。所有命令复用正式 `JsonScenarioCatalogLoader`、`ScenarioCatalog`、`ContentCatalog`、`GameState` 和 `DeterministicStoryDirector`；不读取 `.env`，不连接数据库，不调用 NarrativeProvider，也不发送网络请求。

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

## new：创建隔离草案

`new` 只构造通用 DRAFT 结构，不创作正式剧情。推荐把输出放在 `scenario-drafts` 等非正式目录：

```powershell
.\.venv\Scripts\python.exe -m deviation_protocol.tools.scenario new `
    --scenario-id abandoned_station_v1 `
    --title "废弃车站" `
    --premise "玩家在封闭车站中寻找离开的条件" `
    --output-dir .\scenario-drafts
```

可选参数为 `--content-version`、`--schema-version 1`、`--dry-run` 和 `--json`。未提供 content version 时，CLI 每次都通过正式 `JsonContentCatalogLoader` 从当前 `config/demo_content_pack.json` 读取版本，不维护散落默认字符串；显式版本必须与该正式目录相同。当前只支持严格整数的 Scenario schema 1；未知版本及布尔、浮点或字符串类型直接拒绝。没有 `--force`、`--overwrite` 或自动合并。

生成布局是一个全新的 scenario 专属目录：

```text
<output-dir>/
  <scenario-id>/
    scenario.json
    design.md
```

`scenario.json` 是正式 loader 可读的最小 ScenarioCatalog 草案：包含显式 DRAFT 状态、一个通用初始地点、开局/调查/核心冲突/结算四个占位 phase、三条最小合法 transition 和一个占位 ending。它不包含 NPC、装备、技能、线索、可信事件、outcome rule/token、capability、seal 或脚本表达式。用户提供的 premise 只进入带有 `unverified` 标记的草案摘要，不成为世界事实。内嵌 ContentCatalog 故意为空；需要 preview 时用匹配版本的外部 content pack 和真实可玩角色替换它。

`design.md` 标记为 DRAFT，记录 `scenario-scaffold-v1` 模板版本、scenario ID、title、未验证 premise、人工待填写清单及后续命令。title 与 premise 先做 NFC 和有界空白规范化、拒绝控制字符，再作为缩进代码块中的数据写入，不能创建 Markdown fence、heading 或 HTML comment 结构。相同规范化参数会产生字节级相同的 JSON、Markdown、文件摘要和 digest；组合 digest 使用有域标签的文件名/内容长度前缀编码，不依赖可歧义拼接。内容中不加入时间、随机数、UUID、绝对路径或机器信息。

### dry-run

`--dry-run` 输出将生成的相对文件列表、结构/内容摘要、每个文件的 SHA-256 和组合 digest，但不创建 output directory、临时目录或文件：

```powershell
.\.venv\Scripts\python.exe -m deviation_protocol.tools.scenario new `
    --scenario-id abandoned_station_v1 `
    --title "废弃车站" `
    --premise "玩家在封闭车站中寻找离开的条件" `
    --output-dir .\scenario-drafts `
    --dry-run --json
```

### 不覆盖与目录级原子发布

scenario ID 先通过 ASCII 安全 ID、路径穿越、绝对路径/驱动器/UNC、ADS 冒号、控制字符、结尾点号/空格、长度和 Windows 保留设备名（含扩展名）检查。解析后的最终目录和 staging 目录必须是 output directory 的直接子项；output directory 的任何已有路径组件为 symlink/junction/reparse point、已有 scenario 目录（包括空目录）、任一已有目标文件或已有 staging 目录都会使整个命令拒绝。`config/scenarios` 及其任何内部路径在 dry-run 和实际写入中都被代码拒绝，正式提升只能人工复制并审查。

两个文件先在内存中构造并通过正式 `ScenarioCatalog` 与 analyzer；随后写入 output directory 同卷、以 scenario ID 摘要命名且排他创建的本次专属 staging 目录，再从 staging `scenario.json` 通过正式 `JsonScenarioCatalogLoader`、catalog 与 analyzer，并核对精确字节、每文件 SHA-256 和组合 digest。全部成功后，Windows 上使用 `os.rename` 一次发布整个目录；Windows 的该调用在目标已存在时失败，因此检查后的并发目标创建也不会被覆盖，两个并发 `new` 最多一个成功。实现不使用 `os.replace`、`Path.replace` 或合并逻辑。

Python 标准库在 POSIX 上的目录 `rename` 可以替换已有空目录，且没有可移植的原子 no-replace 选项。本阶段因此只在 Windows 启用实际目录发布；其他平台返回稳定的 platform-unsupported 错误并保留目标，而不是虚假宣称跨平台原子 no-replace。Windows 最终目录只会以包含两个完整文件的形态出现，不宣称两个独立文件具有跨文件系统事务原子性。

第二个文件写入、验证或发布失败时不会留下本工具创建的 final directory。清理只触及记录了创建身份且身份仍匹配的本次 staging 目录、两个固定文件名，以及身份仍匹配且仍为空的本次新建父目录；不使用 glob、递归删除或父目录树清扫。已有 staging 被视为来历不明并保持不动。若进程崩溃，staging 可能残留，下一次运行会拒绝并要求人工检查，而不会自动认领或删除。

这些检查针对误操作、正常并发和可观测的 staging 身份替换。仅靠 Python 路径 API 无法消除同权限恶意本地进程在身份检查与后续 open/rename/rmdir 之间的所有 TOCTOU；本工具不声称抵御能持续篡改同一目录的本地攻击者，也不为此引入原生扩展、后台锁服务或第三方依赖。

### 后续 validate / analyze / preview

```powershell
$scenario = ".\scenario-drafts\abandoned_station_v1\scenario.json"
.\.venv\Scripts\python.exe -m deviation_protocol.tools.scenario validate $scenario
.\.venv\Scripts\python.exe -m deviation_protocol.tools.scenario analyze $scenario
.\.venv\Scripts\python.exe -m deviation_protocol.tools.scenario preview $scenario `
    --content-pack .\config\demo_content_pack.json `
    --character-id character.player.default
```

preview 的 content pack 必须使用同一正式 content version。Workbench 不会生成剧情、NPC、装备、技能或 Python 测试代码，也不会修改 `config/scenarios`、正式 scenario 索引、ContentCatalog、Git 或输入 content pack。作者必须人工完成剧情、规则、隐藏信息与内容审查，重新运行 validate/analyze/preview 和项目测试，然后才可以手动把完成内容复制到正式目录并显式维护对应索引与测试；脚手架不会自动提升草案。

## validate

`validate` 直接通过现有严格 loader 和 `ScenarioCatalog`，不会在 CLI 中维护第二套验证器。它覆盖现有模型已经实施的 JSON/重复 key、schema/content version、额外字段、ID 与交叉引用、必要阶段可达性、自动循环上界、事实变化、decision cadence、outcome effect 边界、声明式 memory rules，以及文件大小、嵌套、集合和字符串限制。正式目录验证成功后还会运行有界静态分析；若存在阻断级诊断，输出验证摘要并退出 `2`，不会以成功退出码掩盖 analyzer 的错误。

### 声明式 memory rules

每个 scenario 的 `memory_rules` 可为空，因此既有微型场景和 scaffold 无需声明长期记忆。规则只能从封闭的可信 source event type 中选择，并指定一个固定 operation；可选条件仅限已验证的 narrative outcome rule ID、scenario event type、outcome result 或 scenario completion。NPC、fact、ending、milestone、significant experience category/summary 必须引用当前内容包和封闭枚举，重要经历还必须使用 category 对应的固定 summary code。Loader 拒绝重复 rule ID、未知事件、extra 字段、不兼容 operation、无效/不可达引用和不稳定组合。

内容包不能提供 event receipt、seal、capability、脚本、任意字段路径、任意 `setattr` 或模型自由文本映射。规则按稳定 ID 执行，同一可信事件触发多条规则时由生产事务整体应用。Workbench 只校验和展示结构，不签发 receipt、不运行生产记忆 mutation，也不根据 catalog 中存在 NPC 就推断玩家已结识。

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

Workbench 不包含文学内容生成器、自动修复、正式文件改写、覆盖/强制发布、GUI、HTML 报告、后台服务、数据库读取、模型质量评价、Provider/DeepSeek 调用、战斗、异常、完整路径穷举、随机模拟或 Token 计费请求。
