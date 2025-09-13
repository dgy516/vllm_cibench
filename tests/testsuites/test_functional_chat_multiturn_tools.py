"""多轮 + tools + response_format 组合用例。"""

from __future__ import annotations

import json

import pytest

from vllm_cibench.clients.openai_client import OpenAICompatClient
from vllm_cibench.testsuites.functional import run_basic_chat


@pytest.mark.functional
def test_chat_multiturn_with_tools_and_json_schema(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"

    # 服务返回最终 JSON 内容
    final_json = {"city": "beijing", "temp_c": 28}
    payload = {
        "id": "chatcmpl-xyz",
        "object": "chat.completion",
        "created": 0,
        "model": "dummy",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(final_json),
                },
                "finish_reason": "stop",
            }
        ],
    }
    requests_mock.post(url, json=payload, status_code=200)

    # 多轮消息 + 工具调用（上一轮由 assistant 触发 tool_calls，随后 tool 角色回显结果）
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "What's the weather?"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"city":"beijing"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "content": json.dumps({"city": "beijing", "temp_c": 28}),
        },
        {"role": "user", "content": "Format as json."},
    ]

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
    schema = {
        "type": "object",
        "properties": {"city": {"type": "string"}, "temp_c": {"type": "number"}},
        "required": ["city", "temp_c"],
    }

    client = OpenAICompatClient(base_url=base)
    out = run_basic_chat(
        client,
        model="dummy",
        messages=messages,
        tools=tools,
        tool_choice="required",
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "Weather", "schema": schema},
        },
        temperature=0,
    )

    body = json.loads(requests_mock.request_history[0].text)
    assert body["tools"][0]["function"]["name"] == "get_weather"
    assert body["tool_choice"] == "required"
    assert len(body["messages"]) == len(messages)
    data = json.loads(out["choices"][0]["message"]["content"])
    assert data["city"] == "beijing" and data["temp_c"] == 28
