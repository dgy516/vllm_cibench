"""功能测试执行器（OpenAI 兼容）单元测试。"""

from __future__ import annotations

import json
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


def test_run_basic_chat_stream(requests_mock):
    """stream 模式应返回按顺序排列的 chunk。"""

    base = "http://example.com/v1"
    url = base + "/chat/completions"
    content = (
        'data: {"choices":[{"index":0,"delta":{"content":"He"}}]}\n\n'
        'data: {"choices":[{"index":0,"delta":{"content":"llo"}}]}\n\n'
        "data: [DONE]\n\n"
    )
    requests_mock.post(
        url,
        content=content.encode(),
        headers={"Content-Type": "text/event-stream"},
        status_code=200,
    )

    client = OpenAICompatClient(base_url=base)
    out = run_basic_chat(
        client,
        model="dummy",
        messages=[{"role": "user", "content": "hi"}],
        stream=True,
    )
    assert len(out) == 2
    assert out[0]["choices"][0]["delta"]["content"] == "He"
    assert out[1]["choices"][0]["delta"]["content"] == "llo"


def test_run_basic_chat_multi_turn(requests_mock):
    """多轮对话应完整携带历史消息。"""

    base = "http://example.com/v1"
    url = base + "/chat/completions"
    payload = _fake_openai_response()
    requests_mock.post(url, json=payload, status_code=200)

    client = OpenAICompatClient(base_url=base)
    messages = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "Hello"},
        {"role": "user", "content": "How are you?"},
    ]
    out = run_basic_chat(client, model="dummy", messages=messages)
    body = json.loads(requests_mock.request_history[0].text)
    assert body["messages"] == messages
    assert out["choices"][0]["message"]["content"] == "Hello"
