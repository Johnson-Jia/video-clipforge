#!/usr/bin/env bash
# BGM 音量注入
#
# 将 bgm_volume 值注入到 index.html 的 <audio> 标签的 data-volume 属性。
# 音量值来源: segment_durations.json → meta.bgm_volume。
#
# 用法: bash scripts/inject_bgm_volume.sh [--project-dir DIR] [--volume 0.15]

set -euo pipefail

PROJECT_DIR="."
VOLUME=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --project-dir) PROJECT_DIR="$2"; shift 2 ;;
    --volume) VOLUME="$2"; shift 2 ;;
    *) shift ;;
  esac
done

cd "$PROJECT_DIR"

echo "=== BGM 音量注入 ==="

# 确定音量值
if [ -z "$VOLUME" ]; then
  if [ -s "segment_durations.json" ]; then
    VOLUME=$(python3 -c "
import json
with open('segment_durations.json', 'r', encoding='utf-8') as f:
    d = json.load(f)
v = d.get('meta', {}).get('bgm_volume', '')
print(v if v else '')
" 2>/dev/null || echo "")
  fi
fi

if [ -z "$VOLUME" ]; then
  echo "WARNING: 未找到 bgm_volume，使用默认值 0.15"
  VOLUME="0.15"
fi

echo "BGM volume: $VOLUME"

# 注入到 index.html
if [ ! -s "index.html" ]; then
  echo "FAIL: index.html 不存在"
  exit 1
fi

# 检查是否有 <audio> 标签
if ! grep -q '<audio' index.html; then
  echo "WARNING: index.html 中无 <audio> 标签，跳过注入"
  exit 0
fi

# 替换 data-volume 属性
if grep -q 'data-volume=' index.html; then
  # 已有 data-volume，替换值
  python3 -c "
import re, sys
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
html = re.sub(r'data-volume=\"[^\"]*\"', 'data-volume=\"$VOLUME\"', html)
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f'data-volume 已更新为 {\"$VOLUME\"}')
"
else
  # 无 data-volume，添加到 <audio 标签
  python3 -c "
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
html = html.replace('<audio ', '<audio data-volume=\"$VOLUME\" ', 1)
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f'data-volume=\"$VOLUME\" 已添加到 <audio> 标签')
"
fi

echo "PASS: BGM 音量注入完成"
