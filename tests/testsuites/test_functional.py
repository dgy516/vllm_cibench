"""功能测试执行器（OpenAI 兼容）单元测试。"""

from __future__ import annotations

from typing import Any, Dict

from vllm_cibench.clients.openai_client import OpenAICompatClient
from vllm_cibench.testsuites.functional import run_basic_chat, run_smoke_suite


def _fake_openai_response() -> Dict[str, Any]:
    """构造最小的 OpenAI 兼容响应体。"""

    return {
        "id": "chatcmpl-xyz",
        "object": "chat.completion",
        "created": 0,
        "model": "dummy",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello"},
                "finish_reason": "stop",
            }
        ],
    }


def test_run_basic_chat_ok(requests_mock):
    """基础 chat 测试：应返回 choices[0].message.content。"""

    base = "http://example.com/v1"
    url = base + "/chat/completions"
    payload = _fake_openai_response()
    requests_mock.post(url, json=payload, status_code=200)

    client = OpenAICompatClient(base_url=base)
    out = run_basic_chat(
        client,
        model="dummy",
        messages=[{"role": "user", "content": "hi"}],
        temperature=0,
    )
    assert out["choices"][0]["message"]["content"] == "Hello"


def test_run_smoke_suite(requests_mock):
    """smoke 套件应能以 200 返回基本结构。"""

    base = "http://example.com/v1"
    url = base + "/chat/completions"
    payload = _fake_openai_response()
    requests_mock.post(url, json=payload, status_code=200)

    out = run_smoke_suite(base_url=base, model="dummy")
    assert out["choices"][0]["message"]["content"] == "Hello"
