#!/usr/bin/env bash
# 项目清理（严格白名单保护 + --dry-run 支持）
#
# 用法:
#   bash scripts/cleanup_project.sh <项目目录>           # 执行清理
#   bash scripts/cleanup_project.sh <项目目录> --dry-run # 仅预览，不删除
#
# 核心原则：白名单是真正的保护机制。
# - safe_rm 删除任何文件前必须检查白名单，在白名单中的文件绝对不可删除
# - 只删除"必删列表"中明确列出的文件/目录
# - 不在白名单也不在必删列表中的文件：不动（保守策略）

set -e
export PYTHONIOENCODING=utf-8  # 防 Windows GBK 致 python 中文输出失败（stage7 gate 违规详情含中文）
DRY_RUN=false
PROJECT_DIR=""

for arg in "$@"; do
  case $arg in
    --dry-run) DRY_RUN=true ;;
    *) [ -z "$PROJECT_DIR" ] && PROJECT_DIR="$arg" ;;
  esac
done

if [ -z "$PROJECT_DIR" ]; then
  echo "用法: bash scripts/cleanup_project.sh <项目目录> [--dry-run]"
  exit 1
fi

# 在 cd 前保存脚本绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# repo 根（scripts→clipforge→commands→.claude→repo，4 层）— 定位 workspace/bgm 素材库（不依赖 cwd 层级）
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

cd "$PROJECT_DIR"

# ── 前置检查：score_report.json 必须存在 ──
if [ ! -f "score_report.json" ]; then
  echo "score_report.json 不存在，自动生成..."
  python "$SCRIPT_DIR/../engine/gate.py" --generate-report --project-dir "$(pwd)" || true
  if [ ! -f "score_report.json" ]; then
    echo "警告：score_report.json 生成失败，继续清理（评分数据将无法事后补评）"
  fi
fi

# ── 前置检查：douyin.md 合规（stage7-delivery gate）──
# 防止交付时跳过 stage7-delivery gate 导致 douyin 违规漏网
# （标题字数/数字锚定/标签数/收藏引导/URL/搜索引导）。cleanup 是管线最后一环，
# 此时 douyin.md 必已写完，强制 gate = 让"douyin 违规 = 无法收尾"。
if [ -f "douyin.md" ]; then
  S7_GATE_JSON="$(pwd)/.s7_gate.json"
  python "$SCRIPT_DIR/../engine/gate.py" --skill stage7-delivery --project-dir "$(pwd)" > "$S7_GATE_JSON" 2>/dev/null || true
  S7_HARD=$(python -c "import json,sys;print(json.load(open(sys.argv[1],encoding='utf-8'))['hard_passed'])" "$S7_GATE_JSON" 2>/dev/null)
  if [ "$S7_HARD" != "True" ]; then
    echo "FAIL: stage7-delivery 门禁未通过，douyin.md 存在违规："
    python -c "import json,sys;[print('  -',v['details'][:200]) for v in json.load(open(sys.argv[1],encoding='utf-8')).get('hard_violations',[])]" "$S7_GATE_JSON" 2>/dev/null
    rm -f "$S7_GATE_JSON"
    if [ "$DRY_RUN" = true ]; then
      echo "（DRY-RUN 仅警告；实际清理前须修复 douyin.md 并重跑）"
    else
      echo "修复 douyin.md 后重跑 cleanup。"
      exit 1
    fi
  else
    echo "[OK] stage7-delivery douyin 合规通过"
  fi
  rm -f "$S7_GATE_JSON"
fi

if [ "$DRY_RUN" = true ]; then
  echo "=== 项目清理（DRY RUN — 仅预览） ==="
else
  echo "=== 项目清理 ==="
fi

# ══════════════════════════════════════════════
# Step 1: 白名单：这些文件绝对不可删除（严格保护）
# ══════════════════════════════════════════════
RETAIN_FILES=(
  # 核心产出物
  final.mp4
  final_no_bgm.mp4
  cover.png
  douyin.md
  score_report.json
  # 数据源
  raw_trending.json
  content_ready.txt
  # 微调输入（严格保留，删了就要重跑阶段）
  output.mp4
  output_no_bgm.mp4
  cover.html
  cover_params.json
  index.html
  design.md
  narration_segments.json
  narration.txt
  segment_durations.json
  sentence_timestamps.json
  phase_timings.json
  content.md
  content_summary.md
  narration.mp3
  bgm.wav
  # 评分凭证（gate.py 门禁依赖，删除 → 事后重评失败）
  .assemble_marker.json
  .bgm_pipeline_marker.json
)

# 受保护目录（目录名匹配，连同内部所有动态文件一并保护，防 future 回归误删）
# creative/ 含动态数量的 sNN.html 碎片 + style.css，无法逐个列入文件白名单，故用目录级保护
# assets/ 含项目素材（截图、图片等原始证据），用户要求永久保留，防止渲染后误删
PROTECTED_DIRS=("creative" "assets")

# 构建白名单查找表（O(1) 查找）
declare -A RETAIN_MAP
for f in "${RETAIN_FILES[@]}"; do
  RETAIN_MAP["$f"]=1
done

echo "白名单保护文件 ($(ls -la ${RETAIN_FILES[@]} 2>/dev/null | grep -c '^-'))："
for f in "${RETAIN_FILES[@]}"; do
  if [ -f "$f" ]; then
    echo "  ✅ [保留] $f"
  fi
done
if [ ${#PROTECTED_DIRS[@]} -gt 0 ]; then
  echo "受保护目录 (${#PROTECTED_DIRS[@]})："
  for d in "${PROTECTED_DIRS[@]}"; do
    if [ -d "$d" ]; then
      echo "  ✅ [保护] $d/ ($(ls "$d" 2>/dev/null | wc -l) 文件)"
    fi
  done
fi

# ══════════════════════════════════════════════
# Step 2: 安全删除函数（白名单校验 + 删除前确认）
# ══════════════════════════════════════════════
DELETE_COUNT=0
BLOCKED_COUNT=0

safe_rm() {
  local target="$1"
  local basename_target
  basename_target="$(basename "$target")"

  # 受保护目录检查：删除路径落在受保护目录内一律拦截（保护动态文件如 creative/sNN.html）
  local _d
  for _d in "${PROTECTED_DIRS[@]}"; do
    if [[ "/${target}/" == *"/${_d}/"* ]]; then
      echo "  🛑 [受保护目录] $target — ${_d}/ 下文件不可删除"
      BLOCKED_COUNT=$((BLOCKED_COUNT+1))
      return 1
    fi
  done

  # 白名单校验：在白名单中的文件绝对不删
  if [ -n "${RETAIN_MAP[$basename_target]+x}" ]; then
    echo "  🛑 [白名单拦截] $basename_target — 保留文件不可删除"
    BLOCKED_COUNT=$((BLOCKED_COUNT+1))
    return 1
  fi

  if [ ! -e "$target" ]; then
    return 0  # 文件不存在，跳过
  fi

  if [ "$DRY_RUN" = true ]; then
    echo "  🗑️ [将删除] $target"
  else
    rm -f "$target"
    echo "  🗑️ [已删除] $target"
  fi
  DELETE_COUNT=$((DELETE_COUNT+1))
  return 0
}

safe_rm_rf() {
  local target="$1"

  # 受保护目录检查：受保护目录本身不可递归删除
  local _d
  for _d in "${PROTECTED_DIRS[@]}"; do
    if [[ "/${target}" == *"/${_d}" ]]; then
      echo "  🛑 [受保护目录] $target/ — ${_d}/ 不可删除"
      BLOCKED_COUNT=$((BLOCKED_COUNT+1))
      return 1
    fi
  done

  if [ ! -e "$target" ]; then
    return 0
  fi

  if [ "$DRY_RUN" = true ]; then
    echo "  🗑️ [将删除] $target/ ($(du -sh "$target" 2>/dev/null | cut -f1))"
  else
    rm -rf "$target"
    echo "  🗑️ [已删除] $target/"
  fi
  DELETE_COUNT=$((DELETE_COUNT+1))
  return 0
}

# ══════════════════════════════════════════════
# Step 3: 删除必删文件（仅删除明确列出的文件）
# ══════════════════════════════════════════════
echo ""
echo "--- 删除中间产物 ---"

for f in narration_seg_*.txt narration_seg_*.mp3 narration_seg_*.srt \
         loudnorm_stats.json concat.txt concat_new.txt \
         output_silent.mp4 output_with_audio.mp4 \
         silence_*.mp3 hyperframes.json frame_check.png \
         verify_*.png check_*.png frame_*.png v2_*.png scenes.yaml \
         stage-handoff.json skills-lock.json webreader_checklist.json \
         cover_final.png cover_segment.mp4 narration.srt \
         cover_1frame.mp4 cover_1frame_audio.mp4 cover.ts output.ts \
         cover_clip.mp4 cover_from_render.mp4 .cleaned \
         bgm_orig.wav bgm_pre_norm.wav machine_score.json delivery.md; do
  safe_rm "$f" || true
done
# 注意：.assemble_marker.json 和 .bgm_pipeline_marker.json 是评分凭证（gate.py 门禁据此
# 验证 final.mp4 由 assemble_final.sh 生成、bgm.wav 由 bgm_pipeline.sh 校准）。
# 删除它们会导致事后重评失败（cleanup→重评的先有鸡先有蛋问题）。已移入 RETAIN_FILES 白名单。

# ══════════════════════════════════════════════
# Step 4: 删除临时目录
# ══════════════════════════════════════════════
echo ""
echo "--- 删除临时目录 ---"

for d in "work-*" ".agents" "renders" "snapshots" "backup" "lib" "frames" "frames_check" "segments" "raw_tts" "clips_16x9" ".diag_frames"; do
  for match in $d; do
    if [ -d "$match" ]; then
      safe_rm_rf "$match/"
    fi
  done
done

# ══════════════════════════════════════════════
# Step 5: BGM 副本按条件删除
# ══════════════════════════════════════════════
echo ""
echo "--- BGM 条件删除 ---"

if [ -f bgm.wav ]; then
  BGM_FOUND_IN_LIB=false

  # 方法1：通过 segment_durations.json 的 meta.bgm_source 匹配
  BGM_SOURCE=$(python -c "import json; d=json.load(open('segment_durations.json')); print(d.get('meta',{}).get('bgm_source',''))" 2>/dev/null || echo "")
  if [ -n "$BGM_SOURCE" ] && [ -f "$REPO_ROOT/workspace/bgm/${BGM_SOURCE}" ]; then
    BGM_FOUND_IN_LIB=true
  fi

  # 方法2：按时长匹配素材库中的文件
  if [ "$BGM_FOUND_IN_LIB" = false ]; then
    BGM_DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 bgm.wav 2>/dev/null | cut -d. -f1)
    for f in "$REPO_ROOT"/workspace/bgm/*.mp3 "$REPO_ROOT"/workspace/bgm/*.wav; do
      if [ -f "$f" ]; then
        LIB_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$f" 2>/dev/null | cut -d. -f1)
        if [ "$BGM_DURATION" = "$LIB_DUR" ]; then
          BGM_FOUND_IN_LIB=true
          break
        fi
      fi
    done
  fi

  if [ "$BGM_FOUND_IN_LIB" = true ]; then
    # 从白名单临时移除 bgm.wav 以允许删除
    unset RETAIN_MAP["bgm.wav"]
    safe_rm "bgm.wav"
    if [ $? -eq 0 ]; then
      [ "$DRY_RUN" = false ] && echo "  已删除 bgm.wav（素材库已有）"
    fi
  else
    echo "  保留 bgm.wav（无法确认素材库来源）"
  fi
fi

# ══════════════════════════════════════════════
# Step 6: 清理后验证（只验证核心产出物）
# ══════════════════════════════════════════════
echo ""
echo "--- 验证 ---"

VERIFY_FILES=(
  final.mp4
  final_no_bgm.mp4
  cover.png
  douyin.md
  score_report.json
)

VERIFY_OK=true
for f in "${VERIFY_FILES[@]}"; do
  if [ ! -f "$f" ]; then
    echo "  ❌ 核心产出物 $f 缺失！"
    VERIFY_OK=false
  fi
done

if [ "$VERIFY_OK" = true ]; then
  echo "  ✅ 核心产出物验证通过"
fi

# 统计
echo ""
echo "删除: ${DELETE_COUNT} 个文件/目录"
echo "白名单拦截: ${BLOCKED_COUNT} 次"
echo "项目大小: $(du -sh . 2>/dev/null | cut -f1)"

if [ "$DRY_RUN" = true ]; then
  echo "=== DRY RUN 完成（未实际删除） ==="
  echo "去掉 --dry-run 参数以执行清理"
else
  if [ "$VERIFY_OK" = true ]; then
    echo "=== 清理完成 ==="
    touch .cleaned
  else
    echo "=== 清理完成（但有核心文件缺失） ==="
    exit 1
  fi
fi
