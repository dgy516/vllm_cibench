"""ServiceLauncher 单元测试（最小）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from vllm_cibench.config import Scenario
from vllm_cibench.deploy.service_launcher import ServiceLauncher, _exp_backoff_wait


class _DummyProc:
    def __init__(self) -> None:
        self._terminated = False

    def poll(self) -> None:
        return None

    def terminate(self) -> None:
        self._terminated = True


def test_exp_backoff_wait_success(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def fake_http(url: str, timeout: float = 1.0, headers: dict | None = None):  # type: ignore[override]
        calls["n"] += 1
        # 第三次返回 200
        return (200 if calls["n"] >= 3 else 503), ""

    monkeypatch.setattr("vllm_cibench.deploy.service_launcher.http_get", fake_http)
    ok = _exp_backoff_wait("http://127.0.0.1:9000/health", max_wait_seconds=5)
    assert ok is True and calls["n"] >= 3


def test_service_launcher_start_stop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # 构造最小场景
    s = Scenario(
        id="local_x",
        mode="local",
        served_model_name="m",
        model="M",
        quant="w8a8",
        raw={"base_url": "http://127.0.0.1:9000/v1"},
    )

    # 伪造启动命令，避免真实调用脚本
    def fake_build_cmd(scenario: Scenario, project_root: Path | None = None):  # type: ignore[override]
        return ["bash", "-lc", "echo started"]

    # 伪造 Popen
    def fake_popen(cmd: list[str], stdout: Any, stderr: Any | None = None):  # type: ignore[override]
        stdout.write("dummy\n")
        return _DummyProc()

    monkeypatch.setattr(
        "vllm_cibench.deploy.service_launcher.build_start_command", fake_build_cmd
    )
    monkeypatch.setattr("subprocess.Popen", fake_popen)
    # 探活立即成功
    monkeypatch.setattr(
        "vllm_cibench.deploy.service_launcher._exp_backoff_wait", lambda *a, **k: True
    )

    logs = tmp_path / "logs"
    with ServiceLauncher(s, tmp_path, logs) as sl:
        sl.start()
        ok = sl.wait_ready(max_wait_seconds=1)
        sl.stop()
    assert ok is True
    assert any(p.name.startswith("service_local_x_") for p in logs.iterdir())
