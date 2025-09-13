"""metrics_rename CLI 测试。"""

from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path


def test_metrics_rename_csv(tmp_path: Path):
    src = tmp_path / "in.csv"
    dst = tmp_path / "out.csv"
    with src.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "concurrency",
                "input_len",
                "output_len",
                "latency_p50_ms",
                "throughput_rps",
            ],
        )
        w.writeheader()
        w.writerow(
            {
                "concurrency": 1,
                "input_len": 128,
                "output_len": 128,
                "latency_p50_ms": 50.5,
                "throughput_rps": 12.3,
            }
        )
    cmd = [
        sys.executable,
        str(Path("tools/metrics_rename.py")),
        "--in",
        str(src),
        "--out",
        str(dst),
        "--fmt",
        "csv",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path("src").resolve())
    subprocess.check_call(cmd, env=env)
    text = dst.read_text(encoding="utf-8")
    assert "throughput_requests_per_second" in text
    assert "latency_p50_milliseconds" in text
