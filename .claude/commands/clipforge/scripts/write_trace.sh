#!/bin/bash
# write_trace.sh - Trace 文件生成器
# 生成标准化的 Trace YAML 文件（三类门禁：process/compliance/quality）
# 用法: write_trace.sh <stage> <project_dir> <status> [--process_passed=BOOL] [--compliance_passed=BOOL] [--quality_score=X] [--quality_evaluator=HUMAN|PLAYBACK_DATA] [--constraint_hits=...]
# 示例: write_trace.sh 3 /workspace/2026/05/27/my-project PASSED --process_passed=true --compliance_passed=true --quality_score=0.85 --quality_evaluator=HUMAN
# 输出: 写入 {project_dir}/trace/stage{N}-{timestamp}.yaml

set -euo pipefail

STAGE="${1:-}"
DIR="${2:-}"
STATUS="${3:-}"

if [ -z "$STAGE" ] || [ -z "$DIR" ] || [ -z "$STATUS" ]; then
  echo "用法: write_trace.sh <stage> <project_dir> <status> [--process_passed=BOOL] [--compliance_passed=BOOL] [--quality_score=X] [--quality_evaluator=HUMAN|PLAYBACK_DATA] [--constraint_hits=...]"
  echo "示例: write_trace.sh 3 /workspace/2026/05/27/my-project PASSED --process_passed=true --compliance_passed=true"
  exit 1
fi

# 解析可选参数（默认值）
PROCESS_PASSED="null"
COMPLIANCE_PASSED="null"
QUALITY_SCORE="null"
QUALITY_EVALUATOR="null"
CONSTRAINT_HITS="[]"
NOTES="null"

shift 3
while [ $# -gt 0 ]; do
  case "$1" in
    --process_passed=*)
      PROCESS_PASSED="${1#*=}"
      ;;
    --compliance_passed=*)
      COMPLIANCE_PASSED="${1#*=}"
      ;;
    --quality_score=*)
      QUALITY_SCORE="${1#*=}"
      ;;
    --quality_evaluator=*)
      EVAL="${1#*=}"
      QUALITY_EVALUATOR="\"${EVAL}\""
      ;;
    --constraint_hits=*)
      CONSTRAINT_HITS="${1#*=}"
      ;;
    --notes=*)
      NOTES_VAL="${1#*=}"
      NOTES="\"${NOTES_VAL}\""
      ;;
  esac
  shift
done

# 生成时间戳
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
TRACE_DIR="$DIR/trace"

# 创建 trace 目录
mkdir -p "$TRACE_DIR"

# 写入 Trace 文件
cat > "$TRACE_DIR/stage${STAGE}-${TIMESTAMP}.yaml" << EOF
trace:
  id: "T-stage${STAGE}-${TIMESTAMP}"
  skill_id: "clipforge.stage${STAGE}"
  timestamp: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  status: "${STATUS}"

  gate_report:
    process_passed: ${PROCESS_PASSED}
    compliance_passed: ${COMPLIANCE_PASSED}
    quality_score: ${QUALITY_SCORE}
    quality_evaluator: ${QUALITY_EVALUATOR}
    quality_notes: ${NOTES}

  execution:
    constraint_hits: ${CONSTRAINT_HITS}

  attribution: null
  success_analysis: null
EOF

echo "TRACE_WRITTEN: $TRACE_DIR/stage${STAGE}-${TIMESTAMP}.yaml"
