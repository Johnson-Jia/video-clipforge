#!/usr/bin/env bash
# s6_render.sh — Stage 6 渲染管线（全自动）
#
# 用法: bash scripts/s6_render.sh [--project-dir DIR]
# 无 --project-dir 时检查 CWD 是否为合法项目目录。
#
# 一次性完成: 渲染前检查 → 导演门禁 → BGM 音量校验 → renderbak 隔离 →
#              lint + render → renderbak 恢复 → output_no_bgm 合成 → 音频验证 → 完成门禁（共 12 步）
# 替代原先 8+ 次独立 LLM 调用。
#
# 前置: index.html + narration.mp3 + bgm.wav
# 输出: output.mp4 + output_no_bgm.mp4 + 门禁报告

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_cd_project.sh" && cd_project "$@"

echo "=== Stage 6 渲染管线 ==="

# ── 渲染僵尸进程回收（按年龄判，非数量）──
# 渲染失败的 chrome-headless-shell 若不回收会在并发期累积吃 RAM，
# 导致后续渲染 x264 malloc 连锁失败（17 僵尸事故）。
# ⚠ 不能按数量阈值全局 taskkill //IM：多管线并发时活跃渲染进程本就可达十几个，
# 会误杀其他管线的健康渲染。按进程年龄外科式判定——活跃渲染通常 <10 分钟，
# ≥20 分钟的 chrome-headless-shell 几乎必为失败遗留，逐 PID 清理。
kill_render_zombies() {
  local ZOMBIE_AGE_MIN=40
  # wmic 行尾是 \r\r\n：\r 不入 bash IFS，read 会把 \r 带进 pid 致 taskkill 静默失败——
  # 必须 tr -d '\r' 后再 read，且 pid 再去一次空白（对抗审查 2026-08-16 H1）
  wmic process where "name='chrome-headless-shell.exe'" get ProcessId,CreationDate 2>/dev/null | \
  tr -d '\r' | \
  while read -r created pid; do
    case "$created" in [0-9]*) ;; *) continue ;; esac   # 跳过表头/空行
    pid=$(printf '%s' "$pid" | tr -d '[:space:]')
    [ -n "$pid" ] || continue
    local ts="${created:0:14}"                          # yyyyMMddHHmmss
    [ ${#ts} -eq 14 ] || continue
    local born
    born=$(date -d "${ts:0:4}-${ts:4:2}-${ts:6:2} ${ts:8:2}:${ts:10:2}:${ts:12:2}" +%s 2>/dev/null) || continue
    local age=$(( ($(date +%s) - born) / 60 ))
    if [ "${age:-0}" -ge "$ZOMBIE_AGE_MIN" ]; then
      echo "[WARN] chrome-headless-shell PID=$pid 年龄 ${age}min ≥ ${ZOMBIE_AGE_MIN}min（失败渲染遗留），清理"
      taskkill //F //PID "$pid" >/dev/null 2>&1 || true
    fi
  done
  echo "[OK] 渲染前僵尸预检完成（仅清 ≥${ZOMBIE_AGE_MIN}min 残留，不影响并发活跃渲染）"
}

# ══════════════════════════════════════════════════
# Phase A: 渲染前检查
# ══════════════════════════════════════════════════

# ── Step 1: 确认关键文件存在 ──
echo "--- Step 1/12: 文件存在性检查 ---"
for f in narration.mp3 bgm.wav index.html; do
  if [ ! -s "$f" ]; then
    echo "FAIL: $f 缺失"
    exit 1
  fi
done
echo "[OK] 关键文件存在"

# ── Step 2: 确认 index.html 包含旁白 <audio> 元素 ──
echo "--- Step 2/12: 旁白 <audio> 检查 ---"
AUDIO_COUNT=$(grep -c '<audio[^>]*src="narration\.mp3"' index.html || true)
if [ "$AUDIO_COUNT" -lt 1 ]; then
  echo "FAIL: index.html 缺少 narration.mp3 <audio> 元素（视频将无旁白）"
  exit 1
fi
echo "[OK] 旁白 <audio> 存在 (${AUDIO_COUNT} 个)"

# ── Step 3: 渲染前依赖检查 ──
echo "--- Step 3/12: 渲染前依赖检查 ---"
python "${SCRIPT_DIR}/pre_render_check.py" .
echo "[OK] 依赖检查通过"

# ── Step 4: 导演门禁 — HTML 设计意图验证（Layer 1）──
# 幂等防御性冗余：此处为「渲染前 fail-fast」，在昂贵的 render 前拦截 HTML 设计缺陷，
# 避免空跑渲染。同一 director_gate 还在 assemble（组装后即时校验）、stage6_gate（独立入口自包含）各跑一次，见 clipforge.md §6。
echo "--- Step 4/12: 导演门禁 ---"
python "${SCRIPT_DIR}/director_gate.py" .
echo "[OK] 导演门禁通过"

# ══════════════════════════════════════════════════
# Phase B: 渲染
# ══════════════════════════════════════════════════

# ── Step 5: BGM 音量校验（音量已在组装阶段注入 index.html）──
echo "--- Step 5/12: BGM 音量校验 ---"
BGM_VOL=$(python -c "import json; print(json.load(open('segment_durations.json', encoding='utf-8'))['meta'].get('bgm_volume', 0.15))" 2>/dev/null || echo "0.15")
if [ "$(python -c "print(1 if float('${BGM_VOL}') <= 0 else 0)")" -eq 1 ]; then
    echo "BLOCKED: bgm_volume=${BGM_VOL} <= 0，BGM 静音。回退 Stage 4 重新校准。"
    exit 1
fi
echo "[OK] BGM 音量正常 (${BGM_VOL})，已由组装阶段注入 index.html"

# ── Step 6: 移除非 index composition 文件（避免 HyperFrames 渲染冲突）──
echo "--- Step 6/12: renderbak 隔离 ---"
for f in cover.html index_with_bgm.html cover.html.bak; do
  [ -f "$f" ] && mv "$f" "$f.renderbak"
done
echo "[OK] 非渲染文件已隔离"

# ── Step 7-8: HyperFrames lint + render ──
kill_render_zombies  # 渲染前预检：清失败渲染遗留的 chrome-headless-shell
echo "--- Step 7/12: HyperFrames lint ---"
npx hyperframes@latest lint
echo "--- Step 8/12: HyperFrames render ---"
if ! npx hyperframes@latest render . --output output.mp4 --video-bitrate 5M --workers 2; then
    kill_render_zombies  # 失败分支：回收本次渲染可能遗留的僵尸进程再退出
    echo "FAIL: HyperFrames 渲染失败"
    exit 1
fi
echo "[OK] output.mp4 已渲染"

# ── Step 9: 恢复 renderbak 文件 ──
echo "--- Step 9/12: renderbak 恢复 ---"
for f in cover.html index_with_bgm.html; do
  [ -f "$f.renderbak" ] && mv "$f.renderbak" "$f"
done
rm -f cover.html.bak.renderbak index_with_bgm.html.renderbak
echo "[OK] 已恢复"

# ══════════════════════════════════════════════════
# Phase C: 后处理 + 验证
# ══════════════════════════════════════════════════

# ── Step 10-11: 合成 output_no_bgm.mp4 + 音频验证 ──
echo "--- Step 10/12: 无 BGM 版本合成 ---"
bash "${SCRIPT_DIR}/build_no_bgm.sh"
echo "[OK] output_no_bgm.mp4 已生成"

echo "--- Step 11/12: 渲染后音频验证 ---"
ffprobe -v quiet -show_streams -select_streams a output.mp4 | grep codec_name || {
  echo "FAIL: output.mp4 无音频轨道"
  exit 1
}
ffmpeg -i output.mp4 -af "volumedetect" -f null /dev/null 2>&1 | grep volume || true
echo "[OK] 音频验证通过"

# ── Step 12: Stage 6 完成门禁 ──
echo "--- Step 12/12: Stage 6 完成门禁 ---"
bash "${SCRIPT_DIR}/stage6_gate.sh"
echo "[OK] Stage 6 完成门禁通过"

echo "=== Stage 6 渲染管线完成 ==="
echo "产出: output.mp4 + output_no_bgm.mp4"
echo "下一步: 运行 s7_delivery.sh 进行交付"
