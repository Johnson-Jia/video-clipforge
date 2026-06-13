"""回溯回填 injected_patterns.json — 给历史视频推导注入记录。

历史视频制作时尚无 injected_patterns 落盘机制（批4 之前），无注入记录。
本脚本根据每个视频的内容属性（topic/hook_type/cover/narration 结构）匹配
现有 auto pattern，推导"若当时跑过自进化，这条视频会被注入哪些 pattern"。

语义：内容特征匹配（确定性推导，非编造数据）。pattern 的维度本质就是内容维度
（P-topic-ai = 题材是 AI），所以"视频 topic=AI" ⟺ "会被注入 P-topic-ai"。
供回归分析"具备某维度特征的视频表现如何"。生成的 injected_patterns.json
标注 source: backfill，区别于实时注入（source: realtime，不覆盖）。

用法：cd .claude/commands/clipforge && python scripts/backfill_injected.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

CLIPFORGE_ROOT = Path(__file__).parent.parent          # .claude/commands/clipforge
SCRIPTS_DIR = Path(__file__).parent                    # scripts/
PROJECT_ROOT = CLIPFORGE_ROOT.parent.parent.parent     # video-clipforge/
WORKSPACE = PROJECT_ROOT / "workspace"
sys.path.insert(0, str(SCRIPTS_DIR))   # import auto_evolve
sys.path.insert(0, str(CLIPFORGE_ROOT))  # engine.*

import auto_evolve  # noqa: E402（触发其顶部 sys.path/engine import/CLIPFORGE_CATEGORY）
from auto_evolve import _classify_topic, _read_narration, _read_cover_attrs  # noqa: E402
from engine.attribution import _classify_hook_type  # noqa: E402（统一 hook 口径）
from engine.lib.data_paths import auto_patterns_dir  # noqa: E402

# 逆映射（与 phase3.5 _match_pattern_projects 一致）
TOPIC_UNSLUG = {v: k for k, v in {
    "AI/智能体": "ai", "安全/隐私": "security", "前端/Web": "frontend",
    "系统/底层": "system", "开发工具": "devtools", "数据/后端": "backend",
    "Python/通用": "python", "综合盘点": "misc", "周榜综合": "weekly",
    "专题深度": "special", "其他": "other", "unknown": "unknown",
}.items()}
COVER_UNSLUG = {v: k for k, v in {
    "冷暖对比": "contrast", "暖色主调": "warm", "冷色主调": "cool", "未知": "unknown"
}.items()}


def _load_auto_pattern_dims() -> list[tuple[str, str, str]]:
    """读所有 auto pattern 的 (id, dim, slug) 维度定义。"""
    dims = []
    for fp in sorted(auto_patterns_dir().glob("P-*.yaml")):
        import yaml
        try:
            data = yaml.safe_load(fp.read_text("utf-8"))
        except Exception:
            continue
        if not data or data.get("seed") is True:
            continue
        pid = data.get("id") or fp.stem
        parts = pid.split("-")
        if len(parts) < 3:
            continue
        dim, slug = parts[1], "-".join(parts[2:])
        dims.append((pid, dim, slug))
    return dims


def _infer_injected(topic, hook_type, cover_bias, has_struct, pattern_dims) -> list[str]:
    """根据项目内容属性匹配 auto pattern 维度（确定性推导）。"""
    matched = []
    for pid, dim, slug in pattern_dims:
        if dim == "topic" and TOPIC_UNSLUG.get(slug) == topic:
            matched.append(pid)
        elif dim == "hook" and slug == hook_type:
            matched.append(pid)
        elif dim == "cover" and COVER_UNSLUG.get(slug) == cover_bias:
            matched.append(pid)
        elif dim == "narration" and slug == "structured" and has_struct:
            matched.append(pid)
    return matched


def main():
    pattern_dims = _load_auto_pattern_dims()
    print(f"auto pattern 维度: {[(p[0], p[1]) for p in pattern_dims]}")
    backfilled = 0
    skipped_realtime = 0
    for pf in sorted(WORKSPACE.rglob("performance.json")):
        proj = pf.parent
        inj_file = proj / "injected_patterns.json"
        # 实时注入记录（source=realtime）不覆盖；已 backfill 的重跑更新（pattern 可能变化）
        if inj_file.exists():
            try:
                if json.loads(inj_file.read_text("utf-8")).get("source") == "realtime":
                    skipped_realtime += 1
                    continue
            except Exception:
                pass
        narr = _read_narration(proj)
        hook_type = _classify_hook_type(narr["hook_text"])
        topic = _classify_topic(proj)
        cover_bias = _read_cover_attrs(proj).get("color_bias", "未知")
        has_struct = (narr.get("attrs") or {}).get("has_struct", False)
        matched = _infer_injected(topic, hook_type, cover_bias, has_struct, pattern_dims)
        payload = {
            "source": "backfill",
            "skill": "inferred",
            "category": "github",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "inferred_from": {"topic": topic, "hook_type": hook_type,
                              "cover_bias": cover_bias, "has_struct": has_struct},
            "injected_patterns": [{"id": pid, "kind": "pref", "weight": "", "skill_scope": ""}
                                  for pid in matched],
        }
        inj_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        backfilled += 1
    print(f"backfill 完成: {backfilled} 个历史项目回填, {skipped_realtime} 个实时记录跳过")


if __name__ == "__main__":
    main()
