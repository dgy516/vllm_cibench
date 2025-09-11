"""HTTP 客户端工具的测试。"""

from __future__ import annotations

import pytest

from vllm_cibench.clients.http import wait_for_http


class DummyResp:
    def __init__(self, status_code: int):
        self.status_code = status_code


def test_wait_for_http_success(monkeypatch: pytest.MonkeyPatch):
    """模拟 200 响应应立即返回 True。"""

    def fake_get(url: str, timeout: float) -> DummyResp:
        return DummyResp(200)

    monkeypatch.setattr("requests.get", fake_get)
    assert wait_for_http("http://x") is True


def test_wait_for_http_fail(monkeypatch: pytest.MonkeyPatch):
    """请求持续失败时返回 False。"""

    def fake_get(url: str, timeout: float) -> DummyResp:
        raise RuntimeError("boom")

    monkeypatch.setattr("requests.get", fake_get)
    assert wait_for_http("http://x", timeout_s=0.01, max_attempts=2) is False
