#!/usr/bin/env bash
# s6_render.sh — Stage 6 渲染管线（全自动）
#
# 用法: bash scripts/s6_render.sh [--project-dir DIR]
# 无 --project-dir 时检查 CWD 是否为合法项目目录。
#
# 一次性完成: 渲染前检查 → 导演门禁 → renderbak → lint → 渲染 → 恢复 →
#              BGM 音量注入 → output_no_bgm 合成 → 音频验证 → 完成门禁
# 替代原先 8+ 次独立 LLM 调用。
#
# 前置: index.html + narration.mp3 + bgm.wav
# 输出: output.mp4 + output_no_bgm.mp4 + 门禁报告

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_cd_project.sh" && cd_project "$@"

echo "=== Stage 6 渲染管线 ==="

# ══════════════════════════════════════════════════
# Phase A: 渲染前检查
# ══════════════════════════════════════════════════

# ── Step 1: 确认关键文件存在 ──
echo "--- Step 1/10: 文件存在性检查 ---"
for f in narration.mp3 bgm.wav index.html; do
  if [ ! -s "$f" ]; then
    echo "FAIL: $f 缺失"
    exit 1
  fi
done
echo "[OK] 关键文件存在"

# ── Step 2: 确认 index.html 包含旁白 <audio> 元素 ──
echo "--- Step 2/10: 旁白 <audio> 检查 ---"
AUDIO_COUNT=$(grep -c '<audio[^>]*src="narration\.mp3"' index.html || true)
if [ "$AUDIO_COUNT" -lt 1 ]; then
  echo "FAIL: index.html 缺少 narration.mp3 <audio> 元素（视频将无旁白）"
  exit 1
fi
echo "[OK] 旁白 <audio> 存在 (${AUDIO_COUNT} 个)"

# ── Step 3: 渲染前依赖检查 ──
echo "--- Step 3/10: 渲染前依赖检查 ---"
python "${SCRIPT_DIR}/pre_render_check.py" .
echo "[OK] 依赖检查通过"

# ── Step 4: 导演门禁 — HTML 设计意图验证（Layer 1）──
echo "--- Step 4/10: 导演门禁 ---"
python "${SCRIPT_DIR}/director_gate.py" .
echo "[OK] 导演门禁通过"

# ══════════════════════════════════════════════════
# Phase B: 渲染
# ══════════════════════════════════════════════════

# ── Step 5: BGM 音量校验（音量已在组装阶段注入 index.html）──
echo "--- Step 5/10: BGM 音量校验 ---"
BGM_VOL=$(python -c "import json; print(json.load(open('segment_durations.json', encoding='utf-8'))['meta'].get('bgm_volume', 0.15))" 2>/dev/null || echo "0.15")
if [ "$(python -c "print(1 if float('${BGM_VOL}') <= 0 else 0)")" -eq 1 ]; then
    echo "BLOCKED: bgm_volume=${BGM_VOL} <= 0，BGM 静音。回退 Stage 4 重新校准。"
    exit 1
fi
echo "[OK] BGM 音量正常 (${BGM_VOL})，已由组装阶段注入 index.html"

# ── Step 6: 移除非 index composition 文件（避免 HyperFrames 渲染冲突）──
echo "--- Step 6/10: renderbak 隔离 ---"
for f in cover.html index_with_bgm.html cover.html.bak; do
  [ -f "$f" ] && mv "$f" "$f.renderbak"
done
echo "[OK] 非渲染文件已隔离"

# ── Step 7: HyperFrames lint + render ──
echo "--- Step 7/10: HyperFrames lint ---"
npx hyperframes lint
echo "--- Step 7/10: HyperFrames render ---"
npx hyperframes render . --output output.mp4 --video-bitrate 5M --concurrency 4
echo "[OK] output.mp4 已渲染"

# ── Step 8: 恢复 renderbak 文件 ──
echo "--- Step 8/10: renderbak 恢复 ---"
for f in cover.html index_with_bgm.html; do
  [ -f "$f.renderbak" ] && mv "$f.renderbak" "$f"
done
rm -f cover.html.bak.renderbak index_with_bgm.html.renderbak
echo "[OK] 已恢复"

# ══════════════════════════════════════════════════
# Phase C: 后处理 + 验证
# ══════════════════════════════════════════════════

# ── Step 9: 合成 output_no_bgm.mp4 + 音频验证 ──
echo "--- Step 9/10: 无 BGM 版本合成 ---"
bash "${SCRIPT_DIR}/build_no_bgm.sh"
echo "[OK] output_no_bgm.mp4 已生成"

echo "--- Step 9/10: 渲染后音频验证 ---"
ffprobe -v quiet -show_streams -select_streams a output.mp4 | grep codec_name || {
  echo "FAIL: output.mp4 无音频轨道"
  exit 1
}
ffmpeg -i output.mp4 -af "volumedetect" -f null /dev/null 2>&1 | grep volume || true
echo "[OK] 音频验证通过"

# ── Step 10: Stage 6 完成门禁 ──
echo "--- Step 10/10: Stage 6 完成门禁 ---"
bash "${SCRIPT_DIR}/stage6_gate.sh"
echo "[OK] Stage 6 完成门禁通过"

echo "=== Stage 6 渲染管线完成 ==="
echo "产出: output.mp4 + output_no_bgm.mp4"
echo "下一步: 运行 s7_delivery.sh 进行交付"
