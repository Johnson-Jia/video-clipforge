#!/usr/bin/env bash
# _cd_project.sh — 管线脚本的目录安全锚点
#
# 用法: source 这里的绝对路径/_cd_project.sh && cd_project "$@"
#
# 从参数中解析 --project-dir，cd 过去，验证标记文件存在。
# 无 --project-dir 时检查 CWD 是否合法。两种方式都阻止写入错误目录。

cd_project() {
  local PROJECT_DIR="."
  local _rest=()
  while [[ $# -gt 0 ]]; do
    case $1 in
      --project-dir) PROJECT_DIR="$2"; shift 2 ;;
      *) _rest+=("$1"); shift ;;
    esac
  done

  cd "$PROJECT_DIR" || {
    echo "FATAL: 无法进入目录: $PROJECT_DIR"
    exit 1
  }

  local markers=("narration_segments.json" "design.md" "segment_durations.json")
  local found=false
  for m in "${markers[@]}"; do
    if [ -f "$m" ]; then found=true; break; fi
  done

  if [ "$found" = false ]; then
    echo "FATAL: $(pwd) 非项目目录（无 design.md / narration_segments.json / segment_durations.json）"
    echo "用法: bash scripts/<script>.sh --project-dir workspace/YYYY/MM/DD/<项目名>"
    exit 1
  fi
}
