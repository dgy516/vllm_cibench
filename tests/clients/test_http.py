"""HTTP 客户端测试。"""

from __future__ import annotations

import pytest

from vllm_cibench.clients.http import http_get, wait_for_http, wait_for_ready


def test_http_get_json_ok(requests_mock):
    """返回 200 且 JSON 可解析时，返回解析后的对象。"""

    url = "http://example.com/ok"
    requests_mock.get(url, json={"hello": "world"}, status_code=200)
    code, body = http_get(url, expect_json=True)
    assert code == 200 and body["hello"] == "world"


def test_wait_for_ready_eventually_ok(requests_mock, monkeypatch):
    """前两次失败后成功，最终返回 True。"""

    url = "http://example.com/poll"
    requests_mock.get(url, [{"status_code": 500}, {"status_code": 200}])

    # 加速测试：跳过 sleep
    monkeypatch.setattr("time.sleep", lambda *_args, **_kw: None)
    assert wait_for_ready(url, timeout_seconds=10, interval_seconds=0.01)


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
