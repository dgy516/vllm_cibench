"""流式（SSE）+ response_format=json_schema 缺少必需字段的场景。

说明：服务端返回 200 且内容不满足 schema 的情况由上层消费方判定；
本用例只验证请求体正确传递 response_format，且分块内容缺少字段。
"""

from __future__ import annotations

import json

import pytest

from vllm_cibench.clients.openai_client import OpenAICompatClient
from vllm_cibench.testsuites.functional import run_basic_chat


@pytest.mark.functional
def test_chat_stream_json_schema_missing_required(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"

    # SSE：仅输出 {"city":"beijing"}，缺少必需 temp_c 字段
    content = (
        'data: {"choices":[{"index":0,"delta":{"role":"assistant"}}]}\n\n'
        'data: {"choices":[{"index":0,"delta":{"content":"{\\"city\\":\\"beijing\\"}"}}]}\n\n'
        "data: [DONE]\n\n"
    )
    requests_mock.post(
        url,
        content=content.encode(),
        headers={"Content-Type": "text/event-stream"},
        status_code=200,
    )

    schema = {
        "type": "object",
        "properties": {"city": {"type": "string"}, "temp_c": {"type": "number"}},
        "required": ["city", "temp_c"],
    }

    client = OpenAICompatClient(base_url=base)
    out = run_basic_chat(
        client,
        model="dummy",
        messages=[{"role": "user", "content": "weather?"}],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "Weather", "schema": schema},
        },
        stream=True,
    )

    body = json.loads(requests_mock.request_history[0].text)
    assert body["response_format"]["type"] == "json_schema"
    # 分块缺少 temp_c
    assert out[-1]["choices"][0]["delta"]["content"] == '{"city":"beijing"}'
