"""功能测试参数覆盖：OpenAI 兼容 chat/completions 的典型与边界参数。"""

from __future__ import annotations

import json

from jsonschema import validate

from vllm_cibench.clients.openai_client import OpenAICompatClient
from vllm_cibench.testsuites.functional import run_basic_chat


def _fake_resp(content: str = "ok") -> dict:
    """构造最小成功响应。"""

    return {
        "id": "chatcmpl-xyz",
        "object": "chat.completion",
        "created": 0,
        "model": "dummy",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }


def _fake_tool_resp() -> dict:
    """构造包含 tool_calls 的响应体。"""

    return {
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
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"city":"beijing"}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
    }


def test_temperature_and_top_p_and_top_k(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    requests_mock.post(url, json=_fake_resp(), status_code=200)

    client = OpenAICompatClient(base_url=base)
    out = run_basic_chat(
        client,
        model="dummy",
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.0,
        top_p=1.0,
        top_k=8,
    )
    # 断言请求体包含指定参数
    body = json.loads(requests_mock.request_history[0].text)
    assert body["temperature"] == 0.0
    assert body["top_p"] == 1.0
    assert body["top_k"] == 8
    assert out["choices"][0]["message"]["content"] == "ok"


def test_response_format_json(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    requests_mock.post(url, json=_fake_resp("{}"), status_code=200)

    client = OpenAICompatClient(base_url=base)
    out = run_basic_chat(
        client,
        model="dummy",
        messages=[{"role": "user", "content": "hi"}],
        response_format={"type": "json_object"},
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["response_format"]["type"] == "json_object"
    assert out["choices"][0]["message"]["content"] == "{}"


def test_response_format_json_schema(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    content = json.dumps({"city": "beijing"})
    requests_mock.post(url, json=_fake_resp(content), status_code=200)

    schema = {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
    }

    client = OpenAICompatClient(base_url=base)
    out = run_basic_chat(
        client,
        model="dummy",
        messages=[{"role": "user", "content": "hi"}],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "City", "schema": schema},
        },
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["response_format"]["type"] == "json_schema"
    data = json.loads(out["choices"][0]["message"]["content"])
    validate(instance=data, schema=schema)


def test_function_call_tools(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    requests_mock.post(url, json=_fake_resp(), status_code=200)

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

    client = OpenAICompatClient(base_url=base)
    _ = run_basic_chat(
        client,
        model="dummy",
        messages=[{"role": "user", "content": "hi"}],
        tools=tools,
        tool_choice="auto",
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["tools"][0]["function"]["name"] == "get_weather"
    assert body["tool_choice"] == "auto"


def test_function_call_tool_choice_required(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    requests_mock.post(url, json=_fake_tool_resp(), status_code=200)

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

    client = OpenAICompatClient(base_url=base)
    out = run_basic_chat(
        client,
        model="dummy",
        messages=[{"role": "user", "content": "hi"}],
        tools=tools,
        tool_choice="required",
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["tool_choice"] == "required"
    name = out["choices"][0]["message"]["tool_calls"][0]["function"]["name"]
    assert name == "get_weather"
