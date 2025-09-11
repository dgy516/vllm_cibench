"""HTTP 客户端与健康检查测试。"""

from vllm_cibench.clients.http import http_get, wait_for_ready


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
