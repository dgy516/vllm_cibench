"""collect_and_push.sh 脚本测试。"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def test_collect_and_push_dry_run(tmp_path: Path):
    csv = tmp_path / "perf.csv"
    csv.write_text(
        "concurrency,input_len,output_len,latency_p50_ms,throughput_rps\n1,128,128,50.0,10.0\n",
        encoding="utf-8",
    )
    cmd = [
        "bash",
        "scripts/collect_and_push.sh",
        "--csv",
        str(csv),
        "--model",
        "Qwen3-32B",
        "--quant",
        "w8a8",
        "--scenario",
        "local_demo",
        "--run-type",
        "daily",
        "--dry-run",
    ]
    env = os.environ.copy()
    out = subprocess.check_output(cmd, env=env).decode()
    data = json.loads(out.strip().splitlines()[-1])
    assert data["run_type"] == "daily" and data["dry_run"] is True
    assert "ci_perf_throughput_rps_avg" in data["metrics"]
