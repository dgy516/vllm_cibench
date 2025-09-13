"""多轮 + response_format + 流式（SSE）用例。"""

from __future__ import annotations

import json

import pytest

from vllm_cibench.clients.openai_client import OpenAICompatClient
from vllm_cibench.testsuites.functional import run_basic_chat


@pytest.mark.functional
def test_chat_stream_multiturn_with_response_format(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"

    # 模拟 SSE 分块：先角色，再内容两段，最后 [DONE]
    content = (
        'data: {"choices":[{"index":0,"delta":{"role":"assistant"}}]}\n\n'
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

    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Greet me."},
    ]
    client = OpenAICompatClient(base_url=base)
    out = run_basic_chat(
        client,
        model="dummy",
        messages=messages,
        response_format={"type": "json_object"},
        stream=True,
        temperature=0,
    )

    # 断言请求体包含 response_format 与完整消息
    body = json.loads(requests_mock.request_history[0].text)
    assert body["response_format"]["type"] == "json_object"
    assert body["messages"][0]["role"] == "system" and len(body["messages"]) == 2

    # 断言分块顺序与内容
    assert isinstance(out, list) and len(out) == 3
    assert out[1]["choices"][0]["delta"]["content"] == "He"
    assert out[2]["choices"][0]["delta"]["content"] == "llo"
