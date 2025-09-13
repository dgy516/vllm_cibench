"""参数合法性（负路径）测试。"""

# isort: skip_file

from __future__ import annotations

import pytest
import requests

from vllm_cibench.clients.openai_client import OpenAICompatClient
from vllm_cibench.testsuites.functional import run_basic_chat, run_basic_completion


@pytest.mark.functional
@pytest.mark.validation
def test_chat_invalid_top_p_raises_http_error(requests_mock):
    """非法 top_p 应返回 4xx 并触发 HTTPError。"""

    base = "http://example.com/v1"
    url = base + "/chat/completions"
    err = {"error": {"message": "invalid top_p"}}
    requests_mock.post(url, json=err, status_code=400)

    client = OpenAICompatClient(base_url=base)
    with pytest.raises(requests.HTTPError):
        _ = run_basic_chat(
            client,
            model="dummy",
            messages=[{"role": "user", "content": "hi"}],
            top_p=1.5,
        )


@pytest.mark.functional
@pytest.mark.validation
def test_completions_negative_max_tokens(requests_mock):
    """负数 max_tokens 应返回 4xx 并触发 HTTPError。"""

    base = "http://example.com/v1"
    url = base + "/completions"
    err = {"error": {"message": "max_tokens must be >= 0"}}
    requests_mock.post(url, json=err, status_code=422)

    with pytest.raises(requests.HTTPError):
        _ = run_basic_completion(
            base_url=base,
            model="dummy",
            prompt="Hello",
            max_tokens=-1,
        )


@pytest.mark.functional
@pytest.mark.validation
def test_chat_negative_temperature(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    err = {"error": {"message": "temperature must be >= 0"}}
    requests_mock.post(url, json=err, status_code=400)

    client = OpenAICompatClient(base_url=base)
    with pytest.raises(requests.HTTPError):
        _ = run_basic_chat(
            client,
            model="dummy",
            messages=[{"role": "user", "content": "x"}],
            temperature=-0.1,
        )


@pytest.mark.functional
@pytest.mark.validation
def test_chat_negative_top_k(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    err = {"error": {"message": "top_k must be >= 0"}}
    requests_mock.post(url, json=err, status_code=400)

    client = OpenAICompatClient(base_url=base)
    with pytest.raises(requests.HTTPError):
        _ = run_basic_chat(
            client,
            model="dummy",
            messages=[{"role": "user", "content": "x"}],
            top_k=-1,
        )


@pytest.mark.functional
@pytest.mark.validation
def test_chat_n_zero_invalid(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    err = {"error": {"message": "n must be >= 1"}}
    requests_mock.post(url, json=err, status_code=400)

    client = OpenAICompatClient(base_url=base)
    with pytest.raises(requests.HTTPError):
        _ = run_basic_chat(
            client,
            model="dummy",
            messages=[{"role": "user", "content": "x"}],
            n=0,
        )


@pytest.mark.functional
@pytest.mark.validation
def test_chat_penalties_out_of_range(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    err = {"error": {"message": "penalty out of range"}}
    requests_mock.post(url, json=err, status_code=422)

    client = OpenAICompatClient(base_url=base)
    with pytest.raises(requests.HTTPError):
        _ = run_basic_chat(
            client,
            model="dummy",
            messages=[{"role": "user", "content": "x"}],
            presence_penalty=2.0,
            frequency_penalty=-2.0,
        )


@pytest.mark.functional
@pytest.mark.validation
def test_chat_logit_bias_wrong_type(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    err = {"error": {"message": "logit_bias must be object"}}
    requests_mock.post(url, json=err, status_code=400)

    client = OpenAICompatClient(base_url=base)
    with pytest.raises(requests.HTTPError):
        _ = run_basic_chat(
            client,
            model="dummy",
            messages=[{"role": "user", "content": "x"}],
            logit_bias=[1, 2],
        )


@pytest.mark.functional
@pytest.mark.validation
def test_chat_seed_wrong_type(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    err = {"error": {"message": "seed must be integer"}}
    requests_mock.post(url, json=err, status_code=400)

    client = OpenAICompatClient(base_url=base)
    with pytest.raises(requests.HTTPError):
        _ = run_basic_chat(
            client,
            model="dummy",
            messages=[{"role": "user", "content": "x"}],
            seed="not-int",
        )


@pytest.mark.functional
@pytest.mark.validation
def test_completions_top_p_out_of_range(requests_mock):
    base = "http://example.com/v1"
    url = base + "/completions"
    err = {"error": {"message": "top_p must be in [0,1]"}}
    requests_mock.post(url, json=err, status_code=400)

    with pytest.raises(requests.HTTPError):
        _ = run_basic_completion(
            base_url=base,
            model="dummy",
            prompt="Hello",
            top_p=2.0,
        )


@pytest.mark.functional
@pytest.mark.validation
def test_completions_n_zero_invalid(requests_mock):
    base = "http://example.com/v1"
    url = base + "/completions"
    err = {"error": {"message": "n must be >= 1"}}
    requests_mock.post(url, json=err, status_code=400)

    with pytest.raises(requests.HTTPError):
        _ = run_basic_completion(
            base_url=base,
            model="dummy",
            prompt="Hello",
            n=0,
        )


@pytest.mark.functional
@pytest.mark.validation
def test_completions_logprobs_invalid_type(requests_mock):
    base = "http://example.com/v1"
    url = base + "/completions"
    err = {"error": {"message": "logprobs must be boolean"}}
    requests_mock.post(url, json=err, status_code=400)

    with pytest.raises(requests.HTTPError):
        _ = run_basic_completion(
            base_url=base,
            model="dummy",
            prompt="Hello",
            logprobs="yes",
        )
