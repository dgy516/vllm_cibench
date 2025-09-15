"""Guided Decoding（response_format）+ 流式 正路径覆盖。"""

from __future__ import annotations

import json

import pytest

from vllm_cibench.clients.openai_client import OpenAICompatClient
from vllm_cibench.testsuites.functional import run_basic_chat


@pytest.mark.functional
def test_chat_stream_json_object_positive(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    # 分块可拼接为完整 JSON
    content = (
        'data: {"choices":[{"index":0,"delta":{"content":"{\\"city\\":"}}]}\n\n'
        'data: {"choices":[{"index":0,"delta":{"content":"\\"beijing\\"}"}}]}\n\n'
        "data: [DONE]\n\n"
    )
    requests_mock.post(
        url,
        content=content.encode(),
        headers={"Content-Type": "text/event-stream"},
        status_code=200,
    )

    client = OpenAICompatClient(base_url=base)
    chunks = run_basic_chat(
        client,
        model="dummy",
        messages=[{"role": "user", "content": "weather"}],
        response_format={"type": "json_object"},
        stream=True,
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["response_format"]["type"] == "json_object"
    text = "".join([c["choices"][0]["delta"].get("content", "") for c in chunks])
    obj = json.loads(text)
    assert obj["city"] == "beijing"

