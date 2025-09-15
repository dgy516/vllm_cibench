#!/usr/bin/env bash
# 从性能 CSV 聚合指标并推送至 Prometheus Pushgateway（与项目条件一致）。
#
# 功能：
# - 读取 CSV（字段需包含 throughput_rps/latency_p50_ms 等），
# - 聚合为平均值，构造 ci_perf_* 指标，
# - 调用项目内 Python API（vllm_cibench.metrics.pushgateway）执行推送。
#
# 示例：
#   scripts/collect_and_push.sh \
#     --csv ./artifacts/perf.csv \
#     --run-type daily \
#     --label model=Qwen3-32B --label quant=w8a8 --label scenario=local_single \
#     --gateway-url http://pushgw:9091
#
# 注意：
# - 仅当 run-type=daily 且（未指定 --gateway-url 时）环境变量 PROM_PUSHGATEWAY_URL 存在时会推送；
# - 在 Fork 或非主仓库时，Python API 会自动跳过推送。

set -euo pipefail

usage() {
  cat <<'USAGE'
用法：collect_and_push.sh [选项]

必选：
  -c, --csv PATH           性能 CSV 文件路径

可选：
  -r, --run-type TYPE      运行类型 pr/daily（默认 daily）
      --dry-run            仅打印不推送
  -l, --label K=V          追加标签（可多次），例如 model=Qwen3-32B
      --gateway-url URL    覆盖 PROM_PUSHGATEWAY_URL 环境变量
  -h, --help               显示帮助
USAGE
}

CSV_PATH=""
RUN_TYPE="daily"
DRY_RUN=0
GATEWAY_URL=""
declare -a LABELS

while [[ $# -gt 0 ]]; do
  case "$1" in
    -c|--csv)
      CSV_PATH="$2"; shift 2 ;;
    -r|--run-type)
      RUN_TYPE="$2"; shift 2 ;;
    --dry-run)
      DRY_RUN=1; shift 1 ;;
    -l|--label)
      LABELS+=("$2"); shift 2 ;;
    --gateway-url)
      GATEWAY_URL="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "未知参数：$1" >&2
      usage; exit 2 ;;
  esac
done

if [[ -z "$CSV_PATH" ]]; then
  echo "错误：必须指定 --csv 路径" >&2
  usage
  exit 2
fi
if [[ ! -f "$CSV_PATH" ]]; then
  echo "错误：找不到 CSV 文件：$CSV_PATH" >&2
  exit 1
fi

# 将标签数组转换为 Python 可消费的 dict 形式
PY_LABELS="{}"
if [[ ${#LABELS[@]} -gt 0 ]]; then
  # 简单构造：分割 key=value；忽略不合法项
  PY_LABELS="{"
  first=1
  for kv in "${LABELS[@]}"; do
    if [[ "$kv" == *"="* ]]; then
      key=${kv%%=*}
      val=${kv#*=}
      if [[ $first -eq 1 ]]; then
        PY_LABELS+="'${key//\'/\'\'}':'${val//\'/\'\'}'"
        first=0
      else
        PY_LABELS+=" ,'${key//\'/\'\'}':'${val//\'/\'\'}'"
      fi
    fi
  done
  PY_LABELS+="}"
fi

echo "读取 CSV 并聚合指标：$CSV_PATH"
if [[ $DRY_RUN -eq 1 ]]; then
  echo "[DRY-RUN] 将跳过推送，仅打印聚合指标"
fi

# 运行内联 Python：解析 CSV -> 聚合 -> 可选推送
python - "$CSV_PATH" "$RUN_TYPE" "$DRY_RUN" "$GATEWAY_URL" "$PY_LABELS" <<'PY'
import io
import json
import os
import sys
from typing import Dict, Any

csv_path = sys.argv[1]
run_type = sys.argv[2]
dry_run = bool(int(sys.argv[3]))
gateway_url = sys.argv[4] or None
labels_expr = sys.argv[5]
try:
    labels: Dict[str, str] = json.loads(labels_expr.replace("'", '"')) if labels_expr else {}
except Exception:
    labels = {}

# 允许从任意工作目录运行：将仓库根加入 sys.path（脚本位于 scripts/）
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from vllm_cibench.testsuites.perf import parse_perf_csv  # noqa: E402
from vllm_cibench.metrics.pushgateway import (  # noqa: E402
    metrics_from_perf_records,
    push_metrics,
)

text = open(csv_path, "r", encoding="utf-8").read()
records = parse_perf_csv(text)
agg = metrics_from_perf_records(records)

print("聚合结果：", json.dumps(agg, ensure_ascii=False))

ok = push_metrics(
    job="vllm_cibench",
    metrics=agg,
    labels=labels,
    gateway_url=gateway_url,
    run_type=run_type,
    dry_run=dry_run,
)
print("推送状态：", ok)
PY

exit 0

