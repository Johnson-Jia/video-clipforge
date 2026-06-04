---
name: narration-anchoring
description: narration_anchor 精确标注方法 — 按句拆分、0-index、Phase 断点校准
---

# narration_anchor 精确标注方法

每个 visual_phases 条目**必须**包含 `narration_anchor` 字段：

```json
{
  "focus": "九阶段DAG管线图",
  "visual_type": "timeline",
  "key_data": ["env-check", "content", "design", "..."],
  "narration_anchor": { "start_sentence": 0, "end_sentence": 1 }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `start_sentence` | int | 该 phase 内容在旁白中对应的**第一个句子**的 0-index（Edge TTS 按句号/逗号拆分 SRT） |
| `end_sentence` | int | 该 phase 内容对应的**最后一个句子**的 0-index |

**标注方法**：写完 `text` 后，将旁白按句号拆分为句子列表（Edge TTS 的 SRT 拆分规则），然后为每个 phase 标注对应的起止句子索引。

**示例**：

旁白："九个阶段，通过DAG有向无环图编排。环境检查、内容获取、导演设计、旁白文案、音频制备。每个阶段完成后自动运行门禁校验。通过才进下一阶段，失败就修复重试。整个管线围绕一个核心指标：前三秒留存率。在短视频平台用户划走视频只要一到三秒，前三秒决定生死。"

Edge TTS 拆分（5 句）：
- 0: "九个阶段，通过DAG有向无环图编排。"
- 1: "环境检查、内容获取、导演设计、旁白文案、音频制备。"
- 2: "每个阶段完成后自动运行门禁校验。"
- 3: "通过才进下一阶段，失败就修复重试。"
- 4: "整个管线围绕一个核心指标..."

Phase 标注：
```json
[
  { "focus": "九阶段DAG管线图", "narration_anchor": { "start_sentence": 0, "end_sentence": 1 } },
  { "focus": "黄金3秒留存率", "narration_anchor": { "start_sentence": 2, "end_sentence": 4 } }
]
```

**无 narration_anchor 时的行为**：`phase_calibrator.py` 会按句子数等分（auto-split），精度降低但仍可用。门禁会标记 `auto-split` 的 phase 为 SOFT 警告。
