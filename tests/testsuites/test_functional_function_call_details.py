"""Function Call 细化覆盖：按名选择、多调用、流式+tools 正路径。"""

from __future__ import annotations

import json

import pytest

from vllm_cibench.clients.openai_client import OpenAICompatClient
from vllm_cibench.testsuites.functional import run_basic_chat


@pytest.mark.functional
def test_tool_choice_by_name(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
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
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "get_weather", "arguments": "{}"},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
    }
    requests_mock.post(url, json=payload, status_code=200)

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

    client = OpenAICompatClient(base_url=base)
    out = run_basic_chat(
        client,
        model="dummy",
        messages=[{"role": "user", "content": "hi"}],
        tools=tools,
        tool_choice={"type": "function", "function": {"name": "get_weather"}},
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["tool_choice"]["type"] == "function"
    assert body["tool_choice"]["function"]["name"] == "get_weather"
    name = out["choices"][0]["message"]["tool_calls"][0]["function"]["name"]
    assert name == "get_weather"


@pytest.mark.functional
def test_parallel_tool_calls(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
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
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "f1", "arguments": "{}"},
                        },
                        {
                            "id": "call_2",
                            "type": "function",
                            "function": {"name": "f2", "arguments": "{}"},
                        },
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
    }
    requests_mock.post(url, json=payload, status_code=200)

    client = OpenAICompatClient(base_url=base)
    out = run_basic_chat(
        client,
        model="dummy",
        messages=[{"role": "user", "content": "hi"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "f1",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "f2",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ],
        tool_choice="auto",
    )
    calls = out["choices"][0]["message"]["tool_calls"]
    assert len(calls) == 2 and {c["function"]["name"] for c in calls} == {"f1", "f2"}


@pytest.mark.functional
def test_stream_with_tools_positive(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    # 简化：流式仅返回两段内容与 [DONE]，不强求 tool_calls 的 SSE 细节
    content = (
        'data: {"choices":[{"index":0,"delta":{"role":"assistant"}}]}\n\n'
        'data: {"choices":[{"index":0,"delta":{"content":"ok"}}]}\n\n'
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
            "function": {"name": "get_weather", "parameters": {"type": "object"}},
        }
    ]

    client = OpenAICompatClient(base_url=base)
    out = run_basic_chat(
        client,
        model="dummy",
        messages=[{"role": "user", "content": "hi"}],
        tools=tools,
        tool_choice="auto",
        stream=True,
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert (
        body["stream"] is True and body["tools"][0]["function"]["name"] == "get_weather"
    )
    assert isinstance(out, list) and len(out) == 2
