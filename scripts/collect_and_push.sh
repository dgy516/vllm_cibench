#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage: $(basename "$0") --csv <perf.csv> --model <name> --quant <q> --scenario <sid> [--run-type pr|daily] [--dry-run]

Options:
  --csv FILE         Perf CSV file with headers: concurrency,input_len,output_len,latency_p50_ms,throughput_rps
  --model NAME       Model logical name (e.g., Qwen3-32B)
  --quant Q         Quantization (e.g., w8a8)
  --scenario SID     Scenario id
  --run-type TYPE    Run type: pr (default) or daily
  --dry-run          Skip Pushgateway even if daily
  -h, --help         Show help

Env:
  PROM_PUSHGATEWAY_URL   Pushgateway URL (required for daily pushes)

Example:
  $(basename "$0") --csv /tmp/perf.csv --model Qwen3-32B --quant w8a8 --scenario local --run-type daily --dry-run
USAGE
}

CSV=""; MODEL=""; QUANT=""; SCENARIO=""; RUN_TYPE="pr"; DRY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --csv) CSV="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --quant) QUANT="$2"; shift 2 ;;
    --scenario) SCENARIO="$2"; shift 2 ;;
    --run-type) RUN_TYPE="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$CSV" || -z "$MODEL" || -z "$QUANT" || -z "$SCENARIO" ]]; then
  echo "Error: required options missing" >&2
  usage; exit 2
fi

# Ensure PYTHONPATH includes src so imports work from repo checkout
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${PYTHONPATH:-}:$ROOT_DIR/src"

CSV_PATH="$CSV" MODEL="$MODEL" QUANT="$QUANT" SCENARIO="$SCENARIO" RUN_TYPE="$RUN_TYPE" DRY="$DRY" \
python3 - <<'PY'
import csv, json, os, sys
from typing import Dict, Any, Iterable, Mapping
from vllm_cibench.testsuites.perf import parse_perf_csv
import importlib

csv_path = os.environ.get('CSV_PATH')
model = os.environ.get('MODEL')
quant = os.environ.get('QUANT')
scenario = os.environ.get('SCENARIO')
run_type = os.environ.get('RUN_TYPE','pr')
dry_run = bool(int(os.environ.get('DRY','0')))

text = open(csv_path, 'r', encoding='utf-8').read()
records = parse_perf_csv(text)

def _metrics_from_records(recs: Iterable[Mapping[str, float]]) -> Dict[str, float]:
    thr, p50 = [], []
    for r in recs:
        if 'throughput_rps' in r:
            thr.append(float(r['throughput_rps']))
        if 'latency_p50_ms' in r:
            p50.append(float(r['latency_p50_ms']))
    out: Dict[str, float] = {}
    if thr:
        out['ci_perf_throughput_rps_avg'] = sum(thr) / len(thr)
    if p50:
        out['ci_perf_latency_p50_ms_avg'] = sum(p50) / len(p50)
    return out

agg = _metrics_from_records(records)
labels = {'model': model, 'quant': quant, 'scenario': scenario}

ok = False
try:
    pg = importlib.import_module('vllm_cibench.metrics.pushgateway')
    # call only if module and function exist
    if hasattr(pg, 'push_metrics'):
        ok = pg.push_metrics('vllm_cibench_manual', agg, labels=labels, run_type=run_type, dry_run=dry_run)
except Exception:
    ok = False
print(json.dumps({'pushed': bool(ok), 'metrics': agg, 'labels': labels, 'run_type': run_type, 'dry_run': dry_run}))
PY
