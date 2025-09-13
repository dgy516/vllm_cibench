"""流式（SSE）+ tools 并用用例。"""

from __future__ import annotations

import json

import pytest

from vllm_cibench.clients.openai_client import OpenAICompatClient
from vllm_cibench.testsuites.functional import run_basic_chat


@pytest.mark.functional
def test_chat_stream_with_tools(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"

    # 模拟流式工具调用：第一块携带 tool_calls 基本信息，后续分块补齐 arguments
    content = (
        'data: {"choices":[{"index":0,"delta":{"role":"assistant","tool_calls":[{"index":0,"id":"call_1","type":"function","function":{"name":"get_weather","arguments":"{\\"city\\":"}}]}}]}\n\n'
        'data: {"choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"\\"beijing\\"}"}}]}}]}\n\n'
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
        stream=True,
    )

    body = json.loads(requests_mock.request_history[0].text)
    assert body["tools"][0]["function"]["name"] == "get_weather"
    assert body["tool_choice"] == "required"
    assert body["messages"][0]["role"] == "user"

    # 断言分块结构：第一块携带工具名称，后续分块累计 arguments
    assert isinstance(out, list) and len(out) == 2
    first = out[0]["choices"][0]["delta"]
    assert (
        first.get("tool_calls")
        and first["tool_calls"][0]["function"]["name"] == "get_weather"
    )
    second = out[1]["choices"][0]["delta"]
    assert second.get("tool_calls")
    # 验证 arguments 片段存在
    assert "arguments" in second["tool_calls"][0]["function"]
