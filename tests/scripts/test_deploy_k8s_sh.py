"""deploy_k8s.sh 脚本测试。"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_help():
    out = subprocess.check_output(["bash", "scripts/deploy_k8s.sh", "--help"]).decode()
    assert "Usage:" in out and "kubectl apply" in out


def test_dry_run_without_kubectl(tmp_path: Path, monkeypatch):
    f = tmp_path / "svc.yaml"
    f.write_text("apiVersion: v1\nkind: Service\n", encoding="utf-8")
    env = os.environ.copy()
    env["DRY_RUN"] = "1"
    # Ensure kubectl not required
    subprocess.check_call(["bash", "scripts/deploy_k8s.sh", "-f", str(f)], env=env)
