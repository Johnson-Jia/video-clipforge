#!/usr/bin/env bash
# 渲染前准备检查
#
# 在 HyperFrames 渲染前运行，验证所有必需文件就绪。
# 用法: bash scripts/render_prep.sh [--project-dir DIR]

set -euo pipefail

PROJECT_DIR="${1:-.}"
[ "$PROJECT_DIR" = "--project-dir" ] && PROJECT_DIR="${2:-.}"
cd "$PROJECT_DIR"

FAIL=0

echo "=== 渲染前准备检查 ==="

# 1. index.html 存在
if [ ! -s "index.html" ]; then
  echo "FAIL: index.html 不存在或为空"
  FAIL=1
else
  echo "PASS: index.html ($(wc -c < index.html) bytes)"
fi

# 2. narration.mp3 存在
if [ ! -s "narration.mp3" ]; then
  echo "FAIL: narration.mp3 不存在或为空"
  FAIL=1
else
  echo "PASS: narration.mp3 ($(du -h narration.mp3 | cut -f1))"
fi

# 3. segment_durations.json 存在且有效 JSON
if [ ! -s "segment_durations.json" ]; then
  echo "FAIL: segment_durations.json 不存在"
  FAIL=1
else
  if python -c "import json; json.load(open('segment_durations.json'))" 2>/dev/null; then
    echo "PASS: segment_durations.json 有效 JSON"
  else
    echo "FAIL: segment_durations.json JSON 解析失败"
    FAIL=1
  fi
fi

# 4. BGM 文件检查（可选）
if [ -s "bgm.wav" ]; then
  echo "PASS: bgm.wav 存在"
elif [ -s "bgm.mp3" ]; then
  echo "PASS: bgm.mp3 存在"
else
  echo "WARNING: 无 BGM 文件（将渲染无配乐版本）"
fi

# 5. cover.html 存在（封面渲染需要）
if [ -s "cover.html" ]; then
  echo "PASS: cover.html 存在"
else
  echo "WARNING: cover.html 不存在（封面需单独生成）"
fi

# 6. 磁盘空间检查（至少 2GB）
FREE_GB=$(df -BG . 2>/dev/null | tail -1 | awk '{print $4}' | tr -d 'G')
if [ -n "$FREE_GB" ] && [ "$FREE_GB" -lt 2 ] 2>/dev/null; then
  echo "FAIL: 磁盘空间不足 ${FREE_GB}GB（需要至少 2GB）"
  FAIL=1
else
  echo "PASS: 磁盘空间 ${FREE_GB:-?}GB"
fi

# 7. HTML 实体检查（&amp; 等转义问题）
if grep -q '&amp;\|&lt;\|&gt;' index.html 2>/dev/null; then
  echo "WARNING: index.html 包含 HTML 实体（&amp; &lt; &gt;），渲染前应运行 sanitize_html_entities.py"
fi

echo ""
if [ $FAIL -eq 0 ]; then
  echo "PASS: 渲染准备就绪"
else
  echo "FAIL: 存在阻塞问题，请修复后重试"
fi
exit $FAIL
