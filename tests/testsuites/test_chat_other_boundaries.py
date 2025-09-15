"""Chat 端其他边界：max_tokens、stop 字符串、top_k=0。"""

from __future__ import annotations

import json

import pytest

from vllm_cibench.clients.openai_client import OpenAICompatClient
from vllm_cibench.testsuites.functional import run_basic_chat


def _payload():
    return {
        "id": "chatcmpl-xyz",
        "object": "chat.completion",
        "created": 0,
        "model": "dummy",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": "ok"}}
        ],
    }


@pytest.mark.functional
def test_chat_max_tokens_positive(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    requests_mock.post(url, json=_payload(), status_code=200)
    client = OpenAICompatClient(base_url=base)
    _ = run_basic_chat(
        client, model="dummy", messages=[{"role": "user", "content": "x"}], max_tokens=4
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["max_tokens"] == 4


@pytest.mark.functional
def test_chat_stop_string(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    requests_mock.post(url, json=_payload(), status_code=200)
    client = OpenAICompatClient(base_url=base)
    _ = run_basic_chat(
        client, model="dummy", messages=[{"role": "user", "content": "x"}], stop="END"
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["stop"] == "END"


@pytest.mark.functional
def test_chat_top_k_zero(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    requests_mock.post(url, json=_payload(), status_code=200)
    client = OpenAICompatClient(base_url=base)
    _ = run_basic_chat(
        client, model="dummy", messages=[{"role": "user", "content": "x"}], top_k=0
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["top_k"] == 0

