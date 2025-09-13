"""Chat 端点扩展功能覆盖测试（更多参数）。"""

from __future__ import annotations

import json

import pytest

from vllm_cibench.clients.openai_client import OpenAICompatClient
from vllm_cibench.testsuites.functional import run_basic_chat


@pytest.mark.functional
def test_chat_best_of(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    payload = {
        "id": "chatcmpl-xyz",
        "object": "chat.completion",
        "created": 0,
        "model": "dummy",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": "ok"}}
        ],
    }
    requests_mock.post(url, json=payload, status_code=200)

    client = OpenAICompatClient(base_url=base)
    out = run_basic_chat(
        client,
        model="dummy",
        messages=[{"role": "user", "content": "x"}],
        n=1,
        best_of=3,
        temperature=0,
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["best_of"] == 3 and body["n"] == 1
    assert out["choices"][0]["message"]["content"] == "ok"


@pytest.mark.functional
def test_chat_length_penalty_and_early_stopping(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    payload = {
        "id": "chatcmpl-xyz",
        "object": "chat.completion",
        "created": 0,
        "model": "dummy",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": "ok"}}
        ],
    }
    requests_mock.post(url, json=payload, status_code=200)

    client = OpenAICompatClient(base_url=base)
    out = run_basic_chat(
        client,
        model="dummy",
        messages=[{"role": "user", "content": "x"}],
        length_penalty=1.0,
        early_stopping=True,
        use_beam_search=True,
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["length_penalty"] == 1.0
    assert body["early_stopping"] is True
    assert body["use_beam_search"] is True
    assert out["choices"][0]["message"]["content"] == "ok"

