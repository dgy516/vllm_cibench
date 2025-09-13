"""流式（SSE）+ tools + response_format 的负路径场景。"""

from __future__ import annotations

import json

import pytest

from vllm_cibench.clients.openai_client import OpenAICompatClient
from vllm_cibench.testsuites.functional import run_basic_chat


@pytest.mark.functional
@pytest.mark.validation
def test_stream_with_tools_and_invalid_json_content(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"

    # 最后一个 content 片段不是合法 JSON
    content = (
        'data: {"choices":[{"index":0,"delta":{"role":"assistant","tool_calls":[{"index":0,"id":"call_1","type":"function","function":{"name":"get_weather","arguments":"{\\"city\\":"}}]}}]}\n\n'
        'data: {"choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"\\"beijing\\"}"}}]}}]}\n\n'
        'data: {"choices":[{"index":0,"delta":{"content":"not json"}}]}\n\n'
        "data: [DONE]\n\n"
    )
    requests_mock.post(
        url,
        content=content.encode(),
        headers={"Content-Type": "text/event-stream"},
        status_code=200,
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            },
        }
    ]

    messages = [{"role": "user", "content": "Get weather for Beijing"}]
    client = OpenAICompatClient(base_url=base)
    out = run_basic_chat(
        client,
        model="dummy",
        messages=messages,
        tools=tools,
        tool_choice="required",
        response_format={"type": "json_object"},
        stream=True,
    )

    # 第三个分块是非 JSON 文本，调用方应自行决定是否解析，这里验证确实原样收到
    assert out[-1]["choices"][0]["delta"]["content"] == "not json"
    body = json.loads(requests_mock.request_history[0].text)
    assert body["response_format"]["type"] == "json_object"
