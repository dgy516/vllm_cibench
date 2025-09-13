"""更多功能参数覆盖与负路径。"""

from __future__ import annotations

import json

import pytest

from vllm_cibench.clients.openai_client import OpenAICompatClient
from vllm_cibench.testsuites.functional import run_basic_chat, run_basic_completion


@pytest.mark.functional
def test_function_call_tool_choice_named(requests_mock):
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
    requests_mock.post(url, json=payload, status_code=200)

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
        tool_choice={"type": "function", "function": {"name": "get_weather"}},
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["tool_choice"]["function"]["name"] == "get_weather"
    assert (
        out["choices"][0]["message"]["tool_calls"][0]["function"]["name"]
        == "get_weather"
    )


@pytest.mark.functional
@pytest.mark.validation
def test_chat_best_of_lt_n_invalid(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    err = {"error": {"message": "best_of must be >= n"}}
    requests_mock.post(url, json=err, status_code=400)

    client = OpenAICompatClient(base_url=base)
    with pytest.raises(Exception):
        _ = run_basic_chat(
            client,
            model="dummy",
            messages=[{"role": "user", "content": "x"}],
            n=2,
            best_of=1,
        )


@pytest.mark.functional
def test_completions_stop_token_ids(requests_mock):
    base = "http://example.com/v1"
    url = base + "/completions"
    payload = {
        "id": "cmpl-xyz",
        "object": "text_completion",
        "created": 0,
        "model": "dummy",
        "choices": [{"index": 0, "text": "A"}],
    }
    requests_mock.post(url, json=payload, status_code=200)

    out = run_basic_completion(
        base_url=base,
        model="dummy",
        prompt="Hello",
        stop_token_ids=[50256],
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["stop_token_ids"] == [50256]
    assert out["choices"][0]["text"] == "A"


@pytest.mark.functional
@pytest.mark.validation
def test_completions_echo_invalid_type(requests_mock):
    base = "http://example.com/v1"
    url = base + "/completions"
    err = {"error": {"message": "echo must be boolean"}}
    requests_mock.post(url, json=err, status_code=400)

    with pytest.raises(Exception):
        _ = run_basic_completion(
            base_url=base,
            model="dummy",
            prompt="Hello",
            echo="true",  # wrong type
        )
