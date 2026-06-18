# CLAUDE.md

本文件是 Claude Code 的项目入口。

任何视频制作任务前，**必须先阅读 [`.claude/commands/clipforge.md`](.claude/commands/clipforge.md)** — 9 阶段视频管线、DAG 编排和模式选择的权威工作流定义。

## 什么是 ClipForge

ClipForge 是 AI 驱动的通用短视频制作系统。通过 DAG 编排管线，将任意内容（文本、URL、PDF、GitHub 数据等）转化为抖音就绪的竖屏视频，含旁白、BGM 和封面。内容分类（GitHub、漫画、小说等）通过 `clipforge/categories/` 中的分类配置定义。

**核心管线**：`内容 → 设计 → 旁白 → 音频 → 素材 → 视频 → 交付 → 机器评分 → 清理`

## 架构

- `.claude/commands/clipforge.md` — 主控制器：DAG 语义、模式选择、错误恢复
- `.claude/commands/clipforge/schema.yaml` — Artifact DAG 定义（唯一真相源）
- `.claude/commands/clipforge/stages/` — 阶段执行指南（stage0 ~ stage8，含 stage0.5 选题规划）
- `.claude/commands/clipforge/shared/` — 共享技能（渲染安全、清理规则、定时续期等）
- `.claude/commands/clipforge/categories/` — 分类配置（按分类覆盖数据、风格、音频、交付等规则）
- `.claude/commands/clipforge/engine/` — 自进化引擎（门禁/归因/Trace/探索-利用/相对衰减/回归归因；`freshness.py` 新鲜度计算、`predict.py` 播放量预测，路径经 `lib/data_paths.py` 统一收口）
- `.claude/commands/clipforge/patterns/seed/` — 人工经验模式（静态定义，入库：工艺 pattern + 选题题材库 `topic-*`；运行产生的 auto 模式在 `workspace/evolution/patterns/`）
- `.claude/commands/github-*.md` — 定时编排文件（全自动 SubAgent 调度）
- `.claude/commands/clipforge/scripts/` — 工具脚本（趋势抓取、BGM、自进化、数据迁移）
- `.claude/commands/clipforge/components/` — 视觉组件库（HTML+CSS+JS 模板）
- `evolution-dashboard/` — 自进化可视化仪表盘（独立服务：看数据 + 手动调维度/模式权重，`python server.py` 启动）
- `workspace/evolution/` — 自进化运行数据（经验模式/轨迹/规则演化/阈值，gitignore）

## 核心原则

1. **Schema 即真相。** 所有 artifact 依赖、产出和完成状态定义在 `schema.yaml` 中，不接受其他来源。`generates` 数组中的**所有文件**都存在才算 artifact 完成。
2. **状态即文件。** `generates` 声明的文件存在于磁盘即代表 artifact 完成。无状态数据库。中断后重新运行 `/clipforge` 即自动跳过已完成阶段。
3. **Stage 文档职责分离。** 操作指令（"做什么"）和事故复盘（"为什么这样做"）严格分离。操作指令只写步骤和命令，事故复盘统一放在 Red Flags 和 Common Rationalizations 部分，不内联在操作步骤中。
4. **管线确定化，创意最大化。** 固定操作、流水线步骤、文件校验、状态判断必须用代码/脚本实现，不允许 LLM 判断确定性逻辑。创意和创造性的环节不限制，充分发挥 LLM 能力。具体边界：
   - **必须代码化**：artifact 完成检测、YAML/JSON schema 校验、文件存在性检查、TTS/BGM 处理、HTML 结构验证、渲染调用、封面模板填充、视频合成、清理、环境检测
   - **LLM 自由发挥**：内容分析摘要、视觉风格推导、旁白文案撰写、HTML 创意内容（CSS 特效/动画设计）、封面文案和配色、平台文案撰写、组件视觉设计
5. **反同质化，多维对齐真实播放量。** score 不只是合规度——`overall_score = 合规·w1 + 新鲜度·w2 + 播放潜力·w3`。满分不再是目标：与近期内容高度相似的视频会被新鲜度拉低分。`stage0.5-topic-plan` 在选题阶段规划题材轮换与新鲜度约束，`freshness.py`/`predict.py` 在评分层量化"像历史的程度"和"播放潜力"。真实播放量经 `/evolve-daily` 回流校准（见命令段）。

## 架构演进验证规范

架构演进（新增 / 改 stage / engine / schema / 管线）完成后**必须双层验证**，不止步于「看起来改了」：

**① 推演核实（subagent + 主 agent 两层）**
- **subagent 全管线推演**：读真实文件 + 每结论附 `file:line`，禁止臆测，找流程断裂 / 不一致 / 遗漏
- **主 agent 独立核实**：不盲信 subagent，grep/read 交叉验证每条结论，修正过度解读（如 schema 语义、有意设计）
- 抓「文档 / 代码一致性」问题（如引擎层修了但编排层仍断、文档承诺 HARD gate 但无实现）

**② 真实视频重做（端到端，更强）**
- 推演核实后，用真实内容**完全重做一条视频**，放在 **`workspace/test/<场景>/`** 隔离目录（**不进 `YYYY/MM/DD` 生产路径，避免覆盖真实视频**；freshness 历史扫描自动排除 test 目录，不污染）。用 `/clipforge` 指定 test 目录跑，验证改动在实际管线端到端生效
- **模式：主 agent 协调多 subagent**（一个推演 / 审查 + 一个或多个执行真实视频制作），主 agent 监控各 subagent 的输入输出 + 每阶段结果
- 抓「推演通但实际跑挂」的问题（脚本参数错、文件时序、环境差异）

> 两者互补：推演抓一致性，真实重做抓实际运行。架构演进缺一不可。单轮推演容易在「引擎层修了」止步，编排层断裂 / 实际运行问题需真实重做才能暴露。

## 技能文件写作规则

技能文件的消费者是 LLM，不是人类开发者。所有写作决策以"移除这段文字后 LLM 决策质量是否下降"为唯一评判标准。

### 保留（LLM 做对决策必需）

| 类型 | 说明 | 示例 |
|------|------|------|
| 技术约束 | 描述平台/工具的客观行为限制 | "HyperFrames seek 不执行 CSS animation" |
| 结构化规则表 | 禁止/替换对、Red Flags 表 | 措辞规范表、渲染安全 Red Flags |
| 决策锚点 | 帮助 LLM 在表格未穷举时做对判断 | "白名单机制（只删明确列出的）" |
| 反面案例 | 为开放性决策提供边界条件 | "✗ 科技内容配暖色生活风 → 观感割裂" |
| 通用 Common Rationalizations | 无引擎 Guard Red Flags 覆盖的轻量阶段 | stage0、cleanup-rules |

### 移除或压缩（对 LLM 决策无增量价值）

| 类型 | 处理方式 | 原因 |
|------|---------|------|
| 事故日期 | 移除日期，保留规则 | 日期是 git history 的职责，不是 prompt 的职责 |
| 事故故事 | 移除故事，保留规则 + gate 标注 | LLM 不被故事说服，`HARD，gate: xxx` 更高效 |
| 说服性"原因" | 移除——表格/规则本身已自足 | "前 3 秒是钩子生死线"与 §5 标题重复 |
| 理论基础 | 移除——紧跟的具体表格已自足 | "人眼注意力极限 8-12 秒"→ 切换频率表已包含 |
| 数据来源标注 | 压缩为 `（N 条视频分析验证）` | LLM 不需要"11 万播放"，"数据分析验证"足够 |
| 架构说明 | 压缩为一行执行方式 | "SubAgent-4 内联调用，不走引擎四原子体系" |
| 冗余 Rationalizations | 有引擎 Guard Red Flags 的 stage 移除 | 引擎注入已覆盖相同功能 |

### 实操检查清单

每次修改技能文件时，逐条过：

1. **日期扫描**：文件中不应出现 `YYYY-MM-DD` 格式的日期（除 `design.md` 模板中的日期占位符）
2. **"原因/因为"扫描**：每个 `原因：` 或 `因为` 后面跟的是技术事实还是说服文字？前者保留，后者移除
3. **"核心原则"扫描**：该原则下方是否有具体的规则表/命令/代码示例？有则移除原则，具体内容自足
4. **HARD 标签扫描**：有 `HARD，gate: xxx` 的规则不需要额外解释为什么违反会出问题
5. **Rationalizations 扫描**：该 stage 有引擎 `inject.py` 注入 Guard Red Flags 吗？有则 Rationalizations 表冗余

## 文档编号规范

所有文档（技能文件、规则、机制文档）的章节编排序号遵循：

| 用法 | 形式 | 适用 |
|------|------|------|
| **默认** | 连续整数 `§1`、`§2`…`§10` | 主章节，顺序递增 |
| **特殊情况** | 一位小数 `§N.N`（如 `§6.6`、`§7.1`） | 仅在需细分或带前缀分组时（如 stage 子节 `6.x`） |

**约束**：
- 连续递增，不跳号（`§1`→`§2`，禁止 `§1`→`§3`）
- 禁止字母后缀（`§1.1a`）、多位小数（`§1.1.1`）、双重编号（`§N` 与 `Step N` 混用）
- 重编号必须级联同步所有跨文件引用（rules 的 `source` 字段、其他 md 正文、脚本 `Step N`），改完用 `grep` 验证旧编号零残留

> 此规范适用于所有架构技能文档的改造与升级。

> **适用范围**：`.claude/commands/` 下的技能/规则/机制文档（含 `clipforge.md` 主控制器、`stages/`、`shared/`、`engine/` 文档）。`docs/` 下的设计参考文档（架构设计、自进化架构设计）豁免——它们是理论设计稿，附录与多层小节结构属合理表达。`engine/lint.py` 的 numbering 检查仅扫 `.claude/commands/` 兜底。

## 分类集成

指定分类时，各阶段读取 `categories/{id}.md` 加载分类特定的覆盖规则（数据源、音色、标签等）。通用 stage 文件提供默认值，分类配置只声明差异项。未指定分类时，所有阶段使用内置默认值。

## 命令

| 命令 | 用途 |
|------|------|
| `/clipforge` | 交互式视频制作（手动模式） |
| `/clipforge-category-setup` | 引导创建分类配置 + 定时任务（手动触发） |
| `/clipforge-feedback` | 分析播放数据，校准机器评分（手动触发） |
| `/evolve-daily` | 每日自进化闭环（auto_evolve 全六阶段：采集→分析→pattern/Delta→播放预测训练钩子，全自动 + 自续期） |
| `/clipforge-switch-workspace` | 切换工作目录（写 `~/.claude/clipforge-config.json`，用户级 install 时设非 git 兜底默认；日常 cd 到不同 git 项目即自动切换） |

> 定时任务由 `/clipforge-category-setup` 生成，属于个人配置（gitignore），不入库。`shared/cron-template.md` 提供通用编排骨架。

> 自进化可视化仪表盘：`cd evolution-dashboard && python server.py`（浏览器看全部自进化数据 + 手动调权重，非 slash 命令）。

## 兼容性

- 本项目是 Claude Code 的技能/工作流包，不是独立应用或 API。
- 视频渲染依赖 [HyperFrames](https://github.com/heygen-com/hyperframes)（通过 `npx skills add` 安装）。
- 与通用编码技能冲突时，以 `clipforge.md` 和本文件为准。
- `workspace/` 是输出目录（已 gitignore），项目产出物存放于此。`workspace/evolution/` 存自进化运行数据（经验模式/轨迹/规则演化/阈值）——技能目录只留静态定义，运行数据隔离。
- **技能可 install 到用户级**（`install.sh --global` → `~/.claude/commands/clipforge`）或项目级（默认 `.claude/commands/clipforge`），两种方式功能等价。工作目录（视频输出/evolution/播放数据落哪里）与技能目录解耦，由 `engine/lib/data_paths.py` 四级回退定位：`CLIPFORGE_WORKSPACE` 环境变量 > `git rev-parse` 项目根 > `~/.claude/clipforge-config.json` 配置默认 > cwd。日常 cd 到不同 git 项目即自动切换工作目录；非 git 目录用 `/clipforge-switch-workspace` 设默认。命令文档通过 `shared/clipforge-env.sh` 定位技能目录（用户级 `~/.claude` 优先，项目级 `.claude` 兜底）。
