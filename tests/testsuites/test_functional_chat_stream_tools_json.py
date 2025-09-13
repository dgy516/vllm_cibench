"""流式（SSE）+ tools + response_format 联合用例。"""

from __future__ import annotations

import json

import pytest

from vllm_cibench.clients.openai_client import OpenAICompatClient
from vllm_cibench.testsuites.functional import run_basic_chat


@pytest.mark.functional
def test_chat_stream_with_tools_and_json_object(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"

    # 模拟流式：第一块为 tool_calls 开始，第二块为 arguments 续写，第三块是 content JSON 片段，最后 [DONE]
    content = (
        'data: {"choices":[{"index":0,"delta":{"role":"assistant","tool_calls":[{"index":0,"id":"call_1","type":"function","function":{"name":"get_weather","arguments":"{\\"city\\":"}}]}}]}\n\n'
        'data: {"choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"\\"beijing\\"}"}}]}}]}\n\n'
        'data: {"choices":[{"index":0,"delta":{"content":"{\\"ok\\":true}"}}]}\n\n'
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
                "description": "Get weather by city",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            },
        }
    ]

    messages = [
        {"role": "user", "content": "Get weather for Beijing"},
    ]

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

    body = json.loads(requests_mock.request_history[0].text)
    assert body["tools"][0]["function"]["name"] == "get_weather"
    assert body["tool_choice"] == "required"
    assert body["response_format"]["type"] == "json_object"

    assert isinstance(out, list) and len(out) == 3
    first = out[0]["choices"][0]["delta"]
    assert (
        first.get("tool_calls")
        and first["tool_calls"][0]["function"]["name"] == "get_weather"
    )
    second = out[1]["choices"][0]["delta"]
    assert (
        second.get("tool_calls") and "arguments" in second["tool_calls"][0]["function"]
    )
    third = out[2]["choices"][0]["delta"]
    assert third.get("content") and third["content"].startswith("{")
