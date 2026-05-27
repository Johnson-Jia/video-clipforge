# ClipForge 引擎层设计规范

> 依据 `docs/agent-self-evolution-architecture.md`，独立实现完整运行时引擎层。
> 引擎可用后再逐步迁移现有 stage 文件。

## 1. 设计目标

将当前散落在 markdown 中的隐性约束（"靠 LLM 自觉遵守"）转化为结构化、可校验、可归因的显性机制。

**业务逻辑等价原则**：引擎实现的所有规则均从现有 stage 文件和共享规范中提取，不新增、不遗漏、不改变语义。

## 2. 引擎组件清单

| 组件 | 文件 | 职责 |
|------|------|------|
| 规则解析器 | `engine/lib/rule_parser.py` | 加载 YAML 规则文件，构建 Rule 对象 |
| 正向重述 | `engine/lib/positive_rewrite.py` | 负向→正向转换模板引擎 |
| Delta 管理 | `engine/lib/delta.py` | Delta Rule CRUD + 影子校验 |
| 约束引擎 | `engine/constraints.py` | 规则加载、作用域合并、约束集产出 |
| 门禁引擎 | `engine/gate.py` | HARD + SOFT 校验、产出 GateReport |
| 轨迹采集 | `engine/trace.py` | 执行轨迹记录、查询 |
| 归因引擎 | `engine/attribution.py` | 双层归因（强归因 + 弱归因） |
| 成功分析 | `engine/success_analyzer.py` | 高分案例采集、经验模式提炼 |
| 注入生成器 | `engine/inject.py` | 生成约束 prompt 段（正向重述 + 经验模式） |
| 规则治理 | `engine/governance.py` | 冲突检测、冗余合并、膨胀检查 |

## 3. 规则结构

```yaml
# 每条规则的结构
id: "R-G-001"                     # 全局安全: R-G-*, 内容规范: R-C-*, 渲染: R-R-*, 音频: R-A-*
                                  # stage 特有: R-S2-*, R-S3-*, R-S4-*, R-S6-*, R-S7-*
type: FORBIDDEN_ACTION            # FORBIDDEN_ACTION | FORBIDDEN_SPEECH | FORBIDDEN_LOGIC | FORBIDDEN_METHOD
pattern: "使用绝对化用语"           # 负向描述（存储格式）
positive: "所有表述使用限定性语言，如'可能'、'通常'、'在一定程度上'"  # 正向重述（注入格式）
guardrail: "输出包含'一定'、'绝对'、'必然'等词视为违规"              # 校验用检测描述
detection:
  keywords: ["一定", "绝对", "必然", "最强", "最好", "必备", "神器"]
  regex: null
  semantic_check: true
severity: HARD                    # HARD | SOFT
class: SAFETY                     # SAFETY | EXPERIENTIAL
scope: GLOBAL                     # GLOBAL | SCENE | SKILL
scene: null                       # SCENE 级时指定
skill: null                       # SKILL 级时指定
source: "_shared-rules.md §1"     # 来源追溯
created_at: "2026-05-27"
hit_count: 0
false_positive_count: 0
```

## 4. Skill 声明结构

```yaml
skill:
  meta:
    id: "skill.clipforge.stage4-audio"
    version: "1.0.0"
    type: EXECUTIVE
    tags: ["audio", "tts", "bgm"]
    rigor: STANDARD
  intent:
    objective: "生成 TTS 旁白音频和背景配乐，产出逐段时长数据"
    criteria:
      - "segment_durations.json 存在且格式正确"
      - "narration.mp3 经过 loudnorm 标准化"
      - "bgm.wav 存在且音量已校准"
  boundary:
    scene: null
    rules:
      - ref: "R-G-*"              # 继承全局规则
      - ref: "R-A-*"              # 继承音频规则
      - ref: "R-S4-*"             # Stage 4 特有规则
  gate:
    hard:
      - gate: "file_exists"
        params:
          files: ["segment_durations.json", "narration.mp3", "bgm.wav"]
      - gate: "json_valid"
        params:
          files: ["segment_durations.json"]
          required_keys: ["meta", "segments"]
      - gate: "loudnorm_verified"
        params:
          file: "narration.mp3"
          min_db: -10
      - gate: "bgm_volume_set"
        params:
          file: "segment_durations.json"
          key: "meta.bgm_volume"
      - gate: "no_forbidden_speech"
    soft:
      - gate: "audio_quality"
        threshold: 0.7
    max_retries: 2
  trace:
    capture: true
    level: FULL
    sensitive_fields: []
```

## 5. Gate 校验类型

| Gate 类型 | 检查内容 | 参数 |
|-----------|---------|------|
| `file_exists` | 文件是否存在且非空 | `files: list` |
| `json_valid` | JSON 文件可解析且含必要字段 | `files: list, required_keys: list` |
| `loudnorm_verified` | 音频 loudnorm 达标 | `file: str, min_db: float` |
| `bgm_volume_set` | BGM 音量已写入 segment_durations | `file: str, key: str` |
| `no_forbidden_speech` | 输出文件无违禁词 | （使用规则库关键词） |
| `no_url_in_output` | 输出无 URL | `files: list` |
| `duration_in_range` | 时长在范围内 | `file: str, key: str, min: float, max: float` |
| `scene_count` | 场景数在范围内 | `file: str, key: str, min: int, max: int` |
| `custom` | 自定义 Python 检查函数 | `module: str, function: str` |

## 6. CLI 接口

```bash
# 约束注入 — 生成正向重述后的约束 prompt 段
python engine/inject.py --skill stage4-audio --category github

# 门禁校验 — 检查产出物
python engine/gate.py --skill stage4-audio --project-dir workspace/2026/05/27/test/

# 轨迹记录 — 记录执行结果
python engine/trace.py record --skill stage4-audio --project-dir ... --result pass

# 归因分析 — 分析失败案例
python engine/attribution.py --trace-file traces/test/trace.json

# 成功分析 — 提炼经验模式
python engine/success_analyzer.py --traces-dir traces/ --min-score 0.85

# 规则治理 — 健康检查
python engine/governance.py check
python engine/governance.py stats
```

## 7. 数据存储

```
traces/
└── <project>/
    └── trace.json           # 单项目完整轨迹

deltas/
└── D-<id>.yaml              # Delta Rule 变更记录

patterns/
├── director-toolkit.yaml    # 导演思维（从 _director-toolkit.md 提取）
├── github-highscore.yaml    # GitHub 高分模式（从 feedback 记忆提取）
└── cover-design.yaml         # 封面设计经验（从 feedback-cover-design.md 提取）
```

## 8. 实现顺序

| 阶段 | 组件 | 依赖 |
|------|------|------|
| 1 | `lib/rule_parser.py` | 无 |
| 2 | `lib/positive_rewrite.py` | rule_parser |
| 3 | `lib/delta.py` | rule_parser |
| 4 | `constraints.py` | rule_parser, positive_rewrite |
| 5 | `gate.py` | rule_parser |
| 6 | `trace.py` | 无 |
| 7 | `inject.py` | constraints, gate |
| 8 | `attribution.py` | rule_parser, trace |
| 9 | `success_analyzer.py` | trace |
| 10 | `governance.py` | rule_parser, trace |

## 9. 规则提取映射

从现有文件提取规则的对应关系：

| 规则文件 | 来源 | 规则数（预估） |
|---------|------|-------------|
| `00-global-safety.yaml` | `_shared-rules.md §1 措辞规范` + `§4 视频内容安全` | 12 |
| `01-content-spec.yaml` | `_shared-rules.md §2-3, §5-6` | 15 |
| `02-render-safety.yaml` | `_render-safety.md` 全部 | 20 |
| `03-audio.yaml` | `stage4-audio.md Iron Law + Red Flags` | 10 |
| `stage2.yaml` | `stage2-analysis.md Red Flags` | 5 |
| `stage3.yaml` | `stage3-scenes.md 节奏铁律 + Red Flags` | 8 |
| `stage4.yaml` | `stage4-audio.md Common Rationalizations` | 5 |
| `stage6.yaml` | `stage6-production.md` 相关规则 | 8 |
| `stage7.yaml` | `stage7-delivery.md` 相关规则 | 5 |
| `categories/github.yaml` | `categories/github.md` Red Flags + Rationalizations | 8 |
