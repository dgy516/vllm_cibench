"""Completions 的 suffix 与 best_of 正路径覆盖。"""

from __future__ import annotations

import json

import pytest

from vllm_cibench.testsuites.functional import run_basic_completion


@pytest.mark.functional
def test_completions_suffix_and_best_of_positive(requests_mock):
    base = "http://example.com/v1"
    url = base + "/completions"
    payload = {
        "id": "cmpl-xyz",
        "object": "text_completion",
        "created": 0,
        "model": "dummy",
        "choices": [
            {"index": 0, "text": "A"},
            {"index": 1, "text": "B"},
        ],
    }
    requests_mock.post(url, json=payload, status_code=200)

    out = run_basic_completion(
        base_url=base,
        model="dummy",
        prompt="Hello",
        suffix=" end",
        n=2,
        best_of=3,
        max_tokens=8,
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["suffix"] == " end"
    assert body["n"] == 2 and body["best_of"] == 3
    assert len(out["choices"]) == 2
