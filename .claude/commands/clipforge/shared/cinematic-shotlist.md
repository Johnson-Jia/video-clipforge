# 电影级剪辑字段规范（Cinematic Shotlist）

> ClipForge 分镜的电影级字段（景别/运镜/转场）。创意自由（LLM 选值）+ 流程固化（脚本映射）。
> stage3 填字段（创意轨），stage6/cinematic.py 映射（确定轨）。引用此文档。

## 三字段白名单

### shot_size（景别）
| 值 | 画面 | 用途 |
|----|------|------|
| 大远景 | 人极小+宏大环境 | 建立世界观、史诗 |
| 远景 | 全身+环境 | 交代人与环境 |
| 全景 | 全身 | 动作、姿态 |
| 中景 | 腰以上 | 对话、互动（默认）|
| 近景 | 胸以上 | 表情、情绪 |
| 特写 | 脸/局部 | 放大情绪 |
| 大特写 | 眼/细节 | 感官冲击 |

→ 映射布局密度（`shot_size_to_density`）：特写/大特写=generous（大字少元素）；远景/大远景=compact（小字多元素）；其余 standard。

### camera_move（运镜）
| 值 | GSAP 映射 | 情绪 |
|----|----------|------|
| 固定 | 无动画（默认）| 稳定、客观 |
| 推 | scale 1→1.1 | 强调、揭示 |
| 拉 | scale 1→0.9 | 疏离、收束 |
| 摇 | x+60 | 扫视 |
| 俯仰 | y-60 | 俯仰 |
| 移 | x+80,y-40 | 横移跟随 |
| 跟 | 无相机动画（主体动）| 代入 |
| 手持 | x/y/rotation 抖动 | 纪实、紧张 |
| 环绕 | rotation +5 | 立体、高光 |
| 变焦 | scale 1→1.2 快推 | 悬疑、聚焦 |
| 第一视角 | 无相机动画 | 主观看法 |
| 荷兰角 | rotation -5 静态 | 失衡、不安 |

### transition（转场，镜间：前镜→当前镜）
| 值 | 过渡 | 用途 |
|----|------|------|
| 硬切 | 即时切（默认）| 快节奏、冲突 |
| 叠化 | crossfade 0.4s | 柔和过渡、时间流逝 |
| 淡入 | 当前镜 fade in 0.5s | 引入、新段 |
| 淡出 | 前镜 fade out 0.5s | 收束、结束 |
| 黑场 | 经 opacity:0 过渡 | 段落分隔、强调 |

## 情绪→字段映射（创意轨参考，非强制）

| 情绪节拍 | 推荐景别 | 推荐运镜 | 推荐转场 |
|---------|---------|---------|---------|
| grab（钩子）| 特写 | 推 / 手持 | 硬切 |
| build（铺垫）| 中景 | 固定 / 移 | 硬切 |
| reveal（揭示）| 近景→远景 | 拉 / 环绕 | 叠化 |
| climax（高潮）| 特写 | 手持 / 变焦 | 硬切 |
| settle（沉淀）| 中景 | 固定 | 叠化 / 淡出 |
| summon（行动）| 近景 | 推 | 淡入 |

## 渲染映射规则（确定轨，scripts/cinematic.py）

- **运镜** → GSAP 相机动画（`camera_move_to_gsap`，对 `.scene-content`，场景 duration 内）
- **转场** → phase opacity 过渡（`transition_to_phase`，build_gsap 替换硬切）
- **景别** → 布局密度（`shot_size_to_density`，density_hint，半确定引导组件/字号）

LLM 填字段（创意自由），脚本映射（流程固化）。非法值默认兜底（不阻塞）。

## 接入点

- stage3：LLM 在 `narration_segments.json` 每个 scene 填 `shot_size`/`camera_move`/`transition`（创意选值）
- s6_assemble_html.build_gsap：读 narration_segments，按 camera_move 注入相机动画、按 transition 注入转场（确定轨）
- gate.check_cinematic_fields：软校验白名单（非法默认兜底，记录警告）
