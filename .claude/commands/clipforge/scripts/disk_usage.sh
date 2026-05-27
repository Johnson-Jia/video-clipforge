#!/usr/bin/env bash
# 项目磁盘占用报告
#
# 显示项目目录下各文件的磁盘占用，按大小排序。
# 用法: bash scripts/disk_usage.sh [--project-dir DIR] [--top N]

set -euo pipefail

PROJECT_DIR="."
TOP_N=20

while [[ $# -gt 0 ]]; do
  case $1 in
    --project-dir) PROJECT_DIR="$2"; shift 2 ;;
    --top) TOP_N="$2"; shift 2 ;;
    *) shift ;;
  esac
done

cd "$PROJECT_DIR"

echo "=== 项目磁盘占用 ==="
echo "目录: $(pwd)"
echo ""

# 总大小
echo "--- 总览 ---"
echo "项目总大小: $(du -sh . 2>/dev/null | cut -f1)"
echo ""

# 按类型汇总
echo "--- 按类型 ---"
echo "视频 (.mp4):  $(find . -maxdepth 1 -name '*.mp4' -exec du -ch {} + 2>/dev/null | tail -1 | cut -f1)"
echo "音频 (.mp3):  $(find . -maxdepth 1 -name '*.mp3' -exec du -ch {} + 2>/dev/null | tail -1 | cut -f1)"
echo "音频 (.wav):  $(find . -maxdepth 1 -name '*.wav' -exec du -ch {} + 2>/dev/null | tail -1 | cut -f1)"
echo "HTML (.html): $(find . -maxdepth 1 -name '*.html' -exec du -ch {} + 2>/dev/null | tail -1 | cut -f1)"
echo "图片 (.png):  $(find . -maxdepth 1 -name '*.png' -exec du -ch {} + 2>/dev/null | tail -1 | cut -f1)"
echo ""

# Top N 文件
echo "--- Top ${TOP_N} 大文件 ---"
du -ah . 2>/dev/null | sort -rh | head -n "$TOP_N"
echo ""

# 清理建议
echo "--- 清理建议 ---"
TMP_COUNT=$(find . -maxdepth 1 \( -name 'work-*' -o -name '.agents' -o -name 'narration_seg_*.txt' -o -name 'narration_seg_*.mp3' \) 2>/dev/null | wc -l)
if [ "$TMP_COUNT" -gt 0 ]; then
  TMP_SIZE=$(find . -maxdepth 1 \( -name 'work-*' -o -name '.agents' \) -exec du -sh {} + 2>/dev/null | awk '{sum+=$1} END {print sum}')
  echo "临时文件: ${TMP_COUNT} 个，运行 cleanup_project.sh 可清理"
else
  echo "无临时文件需要清理"
fi
