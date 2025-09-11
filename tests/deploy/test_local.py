"""本地部署启动函数的测试。"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from vllm_cibench.deploy.local import start_local


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
