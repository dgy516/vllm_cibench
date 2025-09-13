"""Completions logprobs/top_logprobs 边界与负路径。"""

from __future__ import annotations

import pytest

from vllm_cibench.testsuites.functional import run_basic_completion


@pytest.mark.functional
@pytest.mark.validation
def test_logprobs_top_logprobs_zero_invalid(requests_mock):
    base = "http://example.com/v1"
    url = base + "/completions"
    err = {"error": {"message": "top_logprobs must be >= 1 when logprobs=True"}}
    requests_mock.post(url, json=err, status_code=400)
    with pytest.raises(Exception):
        _ = run_basic_completion(
            base_url=base,
            model="dummy",
            prompt="hello",
            logprobs=True,
            top_logprobs=0,
        )


@pytest.mark.functional
@pytest.mark.validation
def test_logprobs_top_logprobs_too_large(requests_mock):
    base = "http://example.com/v1"
    url = base + "/completions"
    err = {"error": {"message": "top_logprobs too large"}}
    requests_mock.post(url, json=err, status_code=400)
    with pytest.raises(Exception):
        _ = run_basic_completion(
            base_url=base,
            model="dummy",
            prompt="hello",
            logprobs=True,
            top_logprobs=100,
        )
