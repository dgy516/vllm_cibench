"""Completions 端点更多参数覆盖。"""

from __future__ import annotations

import json

import pytest

from vllm_cibench.testsuites.functional import run_basic_completion


@pytest.mark.functional
def test_completions_suffix_and_stop(requests_mock):
    base = "http://example.com/v1"
    url = base + "/completions"
    payload = {
        "id": "cmpl-xyz",
        "object": "text_completion",
        "created": 0,
        "model": "dummy",
        "choices": [{"index": 0, "text": "Hello"}],
    }
    requests_mock.post(url, json=payload, status_code=200)

    out = run_basic_completion(
        base_url=base,
        model="dummy",
        prompt="Hi",
        suffix="!",
        stop=["\n\n"],
        max_tokens=8,
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["suffix"] == "!"
    assert body["stop"] == ["\n\n"]
    assert body["max_tokens"] == 8
    assert out["choices"][0]["text"] == "Hello"


@pytest.mark.functional
def test_completions_best_of_and_penalties(requests_mock):
    base = "http://example.com/v1"
    url = base + "/completions"
    payload = {
        "id": "cmpl-xyz",
        "object": "text_completion",
        "created": 0,
        "model": "dummy",
        "choices": [{"index": 0, "text": "Hi"}],
    }
    requests_mock.post(url, json=payload, status_code=200)

    out = run_basic_completion(
        base_url=base,
        model="dummy",
        prompt="Hi",
        n=1,
        best_of=2,
        presence_penalty=0.5,
        frequency_penalty=0.1,
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["best_of"] == 2 and body["n"] == 1
    assert body["presence_penalty"] == 0.5 and body["frequency_penalty"] == 0.1
    assert out["choices"][0]["text"] == "Hi"
