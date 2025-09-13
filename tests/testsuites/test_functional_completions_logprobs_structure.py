"""Completions logprobs 结构与边界（正路径）。"""

from __future__ import annotations

import json

import pytest

from vllm_cibench.testsuites.functional import run_basic_completion


@pytest.mark.functional
def test_completions_logprobs_structure(requests_mock):
    base = "http://example.com/v1"
    url = base + "/completions"
    payload = {
        "id": "cmpl-xyz",
        "object": "text_completion",
        "created": 0,
        "model": "dummy",
        "choices": [
            {
                "index": 0,
                "text": "X",
                "logprobs": {
                    "tokens": ["X"],
                    "token_logprobs": [-0.1],
                    "top_logprobs": [[{"token": "X", "logprob": -0.1}]],
                    "text_offset": [0],
                },
            }
        ],
    }
    requests_mock.post(url, json=payload, status_code=200)

    out = run_basic_completion(
        base_url=base,
        model="dummy",
        prompt="Hello",
        logprobs=True,
        top_logprobs=1,
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["logprobs"] is True and body["top_logprobs"] == 1
    lp = out["choices"][0]["logprobs"]
    assert lp["tokens"][0] == "X" and lp["token_logprobs"][0] == -0.1
