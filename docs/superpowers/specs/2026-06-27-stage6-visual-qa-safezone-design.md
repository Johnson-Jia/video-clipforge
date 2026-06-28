# Stage6 视觉 QA 反馈闭环 + 安全区渲染门禁 设计

- **日期**:2026-06-27
- **状态**:已批准设计,待写实施计划
- **背景**:2026-06-27 github-trending 视频经历 4 轮手动修复,暴露 stage6 ProjectFullCard 两类系统性问题:**布局断层**(项目名与头像间距过大、中间空白带)和**内容溢出安全区**(排名顶到 y≈30px、底部标签压到 y≈1850px)。

## 1. 问题根因(代码探索确认)

- **断层根因**:`s6_assemble_html.py` 只对 bg 层做组件注入(`_inject_bg_component`,line 142),**content 层完全靠 SubAgent 手写碎片 + 手补 CSS**。SubAgent 写 HTML 时**看不到渲染结果**,凭空想象间距→反复断层。
- **溢出根因**:`gate.py` 安全区检查(line 3015 `safe_area_bounds`)是**静态 padding 声明累加**,只看 `.phase` 有没有声明 `padding:180/90/220/90`,**不检查渲染后内容实际像素位置**。`height:100%` 配 `box-sizing:border-box` 撑满 padding-box 导致内容溢出,但 padding 声明在→门禁照过→漏检。

## 2. 目标与非目标

**目标**:
- 防溢出:渲染后内容必须在安全区内(竖屏 y∈[180,1700]),HARD 拦截。
- 防断层:给 SubAgent 配「视觉反馈闭环」——渲染后抽帧分析,把客观数据 + 帧回传,SubAgent 据此自行调整布局。

**非目标(明确不做)**:
- ❌ **不固定布局**:不把 project_full_card 焊成模板。CLAUDE.md「创意最大化」原则:组件视觉设计归 LLM 自由。本改造锁的是「边界」和「数据」,不是「布局样式」。
- ❌ **不改 assemble 注入逻辑**:不扩展组件注入到 content 层(那会扼杀创意)。
- ❌ **断层不做 HARD 强制**:空白带是「留白 vs 断层」的创意判断,不归代码下结论。

## 3. 设计哲学:确定 vs 创意的边界

| 归代码(确定化) | 归 LLM(创意最大化) |
|---|---|
| 安全区 y 边界 [180,1700](HARD) | 布局风格、元素组织、间距审美 |
| 抽帧 + PIL 像素扫描逻辑 | 配色、特效、视觉表达 |
| 空白带的**客观坐标/尺寸** | 空白带**是不是断层**(留白 vs 断层) |
| 渲染后内容 y 范围(事实) | 据反馈如何调整布局(创意) |

核心:**代码只到「客观数据」,判断留给 LLM**。LLM 拿数据 + 帧截图自行决定。

## 4. 架构(A+B 组合)

stage6 渲染后新增 QA 反馈环节(B)+ 门禁硬化(A):

```
SubAgent-3 渲染 output.mp4
      ↓
[B] s6_visual_qa.py(新增,独立 QA 阶段)
   ffmpeg 按各场景时间点抽帧 → 调 lib/visual_qa.analyze_frame → visual_qa_report.json + qa_frames/*.png
   回传 SubAgent-3(报告 + 帧截图)
      ↓
SubAgent-3 自审(看见渲染结果)
   看数据(元素 y 分布 / 空白带坐标)+ 帧截图 → 自行判断布局要不要改
   要改 → 调整它自己的布局 → 重渲染 → 回 [B]
   不改 → 继续(非强制)
      ↓
[A] gate.py check_safezone_rendered(新增检查器,HARD)
   抽帧 + analyze_frame + 安全区判断:每场景 content_y ∈ [180,1700]?
   溢出 = HARD 失败(R-S6-safezone-rendered),必拦
      ↓
通过 → output_no_bgm → final
```

**A 与 B 解耦**:
- B 是反馈闭环(质量,LLM 自审,非强制),插在渲染后、门禁前。
- A 是硬门禁(合规,必拦),独立抽帧不依赖 B 跑没跑(鲁棒)。
- 两者共享 `lib/visual_qa.py` 核心分析,避免重复代码。

## 5. 组件设计

### 5.1 共享核心 `engine/lib/visual_qa.py`(新增)

```python
def analyze_frame(frame_path: str, content_threshold: float = 0.05) -> dict:
    """PIL 分析单帧内容分布。
    返回:
      content_y: [ymin, ymax]  密集文本行的 y 范围(竖屏像素)
      blank_bands: [{"y": int, "height": int}, ...]  连续无内容带(客观记录,不判断层)
      row_density: [float, ...]  逐行内容密度(0-1),供 LLM 看分布曲线
      width, height: 帧尺寸
    实现:
      - PIL 灰度,每行统计亮像素占比(>100/255 视为亮)
      - row_density[i] = 亮像素数 / width
      - 内容行:row_density > content_threshold(过滤 bg 零散粒子/光晕)
      - content_y = 内容行的 min/max y
      - blank_bands:连续 row_density ≤ threshold 的行段(height > 50px 才记录,避免噪声)
    """

def check_safezone(content_y: list, orientation: str = "portrait") -> dict:
    """判断内容是否在安全区。
    portrait: [180, 1700](上180 下220,1080×1920)
    landscape: [60, 1860](上60 下60,1920×1080)
    返回 {ok: bool, y_min, y_max, bounds, overflow: "top"/"bottom"/None}
    """

def extract_scene_frames(output_mp4: str, time_points: list, out_dir: str) -> list:
    """ffmpeg 按时间点抽帧到 out_dir,返回 [{"scene":id,"path":..., "t":float}]"""
```

依赖:Pillow(标准库,确认 engine 环境装了)、ffmpeg(管线已有)。

### 5.2 `scripts/s6_visual_qa.py`(新增,B)

```bash
python scripts/s6_visual_qa.py --project-dir <PROJECT_DIR>
```
- 读 `segment_durations.json` → 各场景 actual_duration → 算中段时间点
- `extract_scene_frames` 抽帧到 `PROJECT_DIR/qa_frames/`
- 每帧 `analyze_frame` → 汇总 `visual_qa_report.json`:

```json
{
  "project_dir": "...",
  "output_mp4": "output.mp4",
  "orientation": "portrait",
  "safezone_bounds": [180, 1700],
  "scenes": [
    {
      "id": "s1",
      "frame": "qa_frames/s1.png",
      "t": 2.83,
      "content_y": [250, 1691],
      "safezone": {"ok": true, "overflow": null},
      "blank_bands": [{"y": 400, "height": 120}],
      "note": "⭐ 空白带 120px (>20% 安全区高度),建议关注"  // 仅 >20% 时标
    }
  ]
}
```

- 输出报告路径 + 帧目录,供 SubAgent-3 读 + 看。
- **不退出码失败**(QA 是反馈不是门禁),始终产报告。

### 5.3 `engine/gate.py` `check_safezone_rendered`(新增检查器,A)

- 插入 stage6-production 的检查器列表。
- 逻辑:读 `visual_qa_report.json`(若有,复用);否则自己 `extract_scene_frames` + `analyze_frame`(解耦)。
- 对每场景调 `check_safezone(content_y, orientation)`,任一 `ok=false` → HARD 失败 `R-S6-safezone-rendered`,报告哪个场景 top/bottom 溢出 + 实际 y 值。
- **不查断层**(断层归 B 反馈)。

### 5.4 stage6 流程整合

改 `stages/stage6-production.md` + `shared/cron-template.md`(SubAgent-3 指令段):
- SubAgent-3 渲染 output.mp4 后,**先跑 `s6_visual_qa.py`**,读 visual_qa_report.json + 看 qa_frames 帧截图,自审布局(断层/间距)。不满意自行调整重渲染。
- 自审通过后,跑 `gate.py --skill stage6-production`(现含 check_safezone_rendered HARD)。
- SubAgent-3 prompt 加指令:「渲染后跑 s6_visual_qa.py,看 visual_qa_report.json 的 blank_bands 和 qa_frames 帧截图,判断布局是否有断层/间距问题(创意判断归你),需要则调整重渲染;然后跑门禁(安全区 HARD 必过)」。

## 6. 测试与验证

### 6.1 单元测试(`engine/tests/test_visual_qa.py`,新增)
- `analyze_frame`:用合成帧(已知内容 y 位置)验证 content_y 准确、blank_bands 正确。
- `check_safezone`:边界用例(y=180/1700 边界、溢出 top/bottom、横屏边界)。

### 6.2 回归测试(用 2026-06-27 已修视频)
- 跑 `s6_visual_qa.py`:报告应显示 5 个项目场景 safezone OK + 标出之前修复的断层位置(项目名-头像间距)。
- 跑 `gate.py`:hard_passed(已修,内容在安全区)。

### 6.3 构造溢出测试
- 临时改 creative/style.css 的 pfc inset(如 top:0)制造溢出 → gate check_safezone_rendered 应 HARD 失败。

### 6.4 架构演进双层验证(CLAUDE.md 规范)
- **推演核实**:subagent + 主 agent 两层,读真实文件 + 每结论附 file:line,找流程断裂。
- **真实视频重做**:用真实内容在 `workspace/test/<场景>/` 隔离跑 `/clipforge`,验证改造端到端生效(test 目录被 freshness/evolution 扫描排除,见 feedback-test-isolation)。

## 7. 改动文件清单

| 文件 | 改动 | 类型 |
|---|---|---|
| `engine/lib/visual_qa.py` | 新增(共享分析核心) | 新文件 |
| `scripts/s6_visual_qa.py` | 新增(QA 阶段,B) | 新文件 |
| `engine/gate.py` | 加 `check_safezone_rendered` 检查器 + 注册到 stage6 | 改 |
| `engine/tests/test_visual_qa.py` | 新增单元测试 | 新文件 |
| `stages/stage6-production.md` | SubAgent-3 指令加 QA 自审步骤 | 改 |
| `shared/cron-template.md` | SubAgent-3 prompt 模板加 QA 指令 | 改 |
| `engine/lib/data_paths.py` | 若需加 qa_frames 路径收口(检查) | 可能改 |

## 8. 工作量与风险

- **工作量**:中。核心是 lib/visual_qa.py(分析逻辑)+ gate 检查器 + 流程整合。预计 2-3 个实施单元。
- **风险**:
  - bg 光晕/粒子干扰内容检测→用 content_threshold(行密度 5%)+ blank_bands height>50px 过滤,单元测试校准。
  - Pillow 未装→实施前确认 engine 环境(`python -c "import PIL"`),缺则 requirements 加。
  - QA 抽帧增加 stage6 耗时(每场景 1 帧,~7 帧,开销小可接受)。
