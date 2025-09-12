# isort: skip_file
"""本地部署相关测试。"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from vllm_cibench.config import list_scenarios
from vllm_cibench.deploy.local import (
    build_start_command,
    scenario_base_url,
    wait_service_ready,
    start_local,
)


def test_build_start_command_and_base_url():
    """校验命令拼装包含模型与量化参数，且能取到 base_url。"""

    scenario = next(
        s for s in list_scenarios(Path("configs/scenarios")) if s.mode == "local"
    )
    cmd = build_start_command(scenario, project_root=Path.cwd())
    assert "scripts/start_local.sh" in cmd[1]
    assert "--model" in cmd and scenario.served_model_name in cmd
    assert "--quant" in cmd and scenario.quant in cmd

    url = scenario_base_url(scenario)
    assert url.startswith("http://") or url.startswith("https://")


class DummyProc:
    def __init__(self, cmd, stdout=None, stderr=None):
        self.cmd = cmd
        self.stdout = stdout
        self.stderr = stderr
        self.terminated = False

    def terminate(self) -> None:  # pragma: no cover - 简单 setter
        self.terminated = True


def test_start_local_success(monkeypatch: pytest.MonkeyPatch):
    """探活通过时应返回子进程对象。"""

    def fake_popen(cmd, stdout=None, stderr=None):
        return DummyProc(cmd, stdout, stderr)

    def fake_wait(url: str, timeout_s: float, max_attempts: int) -> bool:
        return True

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr("vllm_cibench.deploy.local.wait_for_http", fake_wait)

    proc = start_local(script=Path("scripts/start_local.sh"), health_url="http://x")
    assert isinstance(proc, DummyProc)
    assert proc.cmd[0] == "bash"


def test_start_local_health_fail(monkeypatch: pytest.MonkeyPatch):
    """探活失败时应终止子进程并抛出异常。"""

    terminated: dict[str, bool] = {"flag": False}

    def fake_popen(cmd, stdout=None, stderr=None):
        class P:
            def __init__(self):
                self.cmd = cmd

            def terminate(self):
                terminated["flag"] = True

        return P()

    def fake_wait(url: str, timeout_s: float, max_attempts: int) -> bool:
        return False

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr("vllm_cibench.deploy.local.wait_for_http", fake_wait)

    with pytest.raises(RuntimeError):
        start_local(script=Path("scripts/start_local.sh"), health_url="http://x")
    assert terminated["flag"] is True


def test_wait_service_ready_uses_scenario_timeout(monkeypatch: pytest.MonkeyPatch):
    """未显式传参时应使用场景配置的 startup_timeout_seconds。"""

    scenario = next(
        s for s in list_scenarios(Path("configs/scenarios")) if s.mode == "local"
    )
    captured: dict[str, int] = {}

    def fake_wait(url: str, timeout_seconds: int, headers=None) -> bool:
        captured["timeout"] = timeout_seconds
        return True

    monkeypatch.setattr("vllm_cibench.deploy.local.wait_for_ready", fake_wait)
    ok = wait_service_ready(scenario)
    assert ok is True
    assert captured["timeout"] == scenario.raw.get("startup_timeout_seconds")


def test_wait_service_ready_override_timeout(monkeypatch: pytest.MonkeyPatch):
    """显式传入 timeout_seconds 时应覆盖场景配置。"""

    scenario = next(
        s for s in list_scenarios(Path("configs/scenarios")) if s.mode == "local"
    )
    captured: dict[str, int] = {}

    def fake_wait(url: str, timeout_seconds: int, headers=None) -> bool:
        captured["timeout"] = timeout_seconds
        return True

    monkeypatch.setattr("vllm_cibench.deploy.local.wait_for_ready", fake_wait)
    wait_service_ready(scenario, timeout_seconds=5)
    assert captured["timeout"] == 5
