"""gen_scenario_yaml CLI 测试。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml


def test_gen_scenario_yaml(tmp_path: Path):
    out = tmp_path / "sc.yaml"
    cmd = [
        sys.executable,
        str(Path("tools/gen_scenario_yaml.py")),
        "--id",
        "local_demo",
        "--mode",
        "local",
        "--model",
        "Qwen3-32B",
        "--served-model-name",
        "qwen3-32b",
        "--quant",
        "w8a8",
        "--out",
        str(out),
    ]
    subprocess.check_call(cmd)
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert data["id"] == "local_demo" and data["mode"] == "local"
