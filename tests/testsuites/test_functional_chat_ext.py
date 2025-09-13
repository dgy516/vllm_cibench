"""Chat 端点扩展功能覆盖测试。"""

from __future__ import annotations

import json

import pytest

from vllm_cibench.clients.openai_client import OpenAICompatClient
from vllm_cibench.testsuites.functional import run_basic_chat


@pytest.mark.functional
def test_chat_n_multi_samples(requests_mock):
    """n 多样本应被传递并返回多个 choices。"""

    base = "http://example.com/v1"
    url = base + "/chat/completions"
    payload = {
        "id": "chatcmpl-xyz",
        "object": "chat.completion",
        "created": 0,
        "model": "dummy",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": "Hi"}},
            {"index": 1, "message": {"role": "assistant", "content": "Hello"}},
        ],
    }
    requests_mock.post(url, json=payload, status_code=200)

    client = OpenAICompatClient(base_url=base)
    out = run_basic_chat(
        client,
        model="dummy",
        messages=[{"role": "user", "content": "greet"}],
        n=2,
        temperature=0,
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["n"] == 2
    assert len(out["choices"]) == 2


@pytest.mark.functional
def test_chat_with_system_and_stop(requests_mock):
    """system 提示与 stop/stop_token_ids 参数应被正确传递。"""

    base = "http://example.com/v1"
    url = base + "/chat/completions"
    payload = {
        "id": "chatcmpl-xyz",
        "object": "chat.completion",
        "created": 0,
        "model": "dummy",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
    }
    requests_mock.post(url, json=payload, status_code=200)

    client = OpenAICompatClient(base_url=base)
    messages = [
        {"role": "system", "content": "You are concise."},
        {"role": "user", "content": "Tell me a joke"},
    ]
    out = run_basic_chat(
        client,
        model="dummy",
        messages=messages,
        stop=["\n\n"],
        stop_token_ids=[50256],
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["messages"][0]["role"] == "system"
    assert body["stop"] == ["\n\n"]
    assert body["stop_token_ids"] == [50256]
    assert out["choices"][0]["message"]["content"] == "ok"


@pytest.mark.functional
def test_chat_penalties_seed_and_logit_bias(requests_mock):
    """presence/frequency penalty、seed、logit_bias 传参与回放。"""

    base = "http://example.com/v1"
    url = base + "/chat/completions"
    payload = {
        "id": "chatcmpl-xyz",
        "object": "chat.completion",
        "created": 0,
        "model": "dummy",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
    }
    requests_mock.post(url, json=payload, status_code=200)

    client = OpenAICompatClient(base_url=base)
    out = run_basic_chat(
        client,
        model="dummy",
        messages=[{"role": "user", "content": "x"}],
        presence_penalty=0.5,
        frequency_penalty=0.1,
        seed=42,
        logit_bias={"123": -1},
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["presence_penalty"] == 0.5
    assert body["frequency_penalty"] == 0.1
    assert body["seed"] == 42
    assert body["logit_bias"]["123"] == -1
    assert out["choices"][0]["message"]["content"] == "ok"
