"""acs_bench_mock CLI 测试。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_acs_bench_mock_cli(tmp_path: Path):
    out = tmp_path / "perf.csv"
    cmd = [
        sys.executable,
        str(Path("tools/acs_bench_mock.py")),
        "--concurrency",
        "1,2",
        "--input-len",
        "128",
        "--output-len",
        "128",
        "--out",
        str(out),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path("src").resolve())
    subprocess.check_call(cmd, env=env)
    text = out.read_text(encoding="utf-8")
    assert "concurrency" in text and "throughput_rps" in text
