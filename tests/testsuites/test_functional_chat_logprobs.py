"""Chat 端点 logprobs/top_logprobs 功能覆盖。"""

from __future__ import annotations

import json

import pytest

from vllm_cibench.clients.openai_client import OpenAICompatClient
from vllm_cibench.testsuites.functional import run_basic_chat


@pytest.mark.functional
def test_chat_logprobs_and_top_logprobs(requests_mock):
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
    _ = run_basic_chat(
        client,
        model="dummy",
        messages=[{"role": "user", "content": "hi"}],
        logprobs=True,
        top_logprobs=2,
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["logprobs"] is True
    assert body["top_logprobs"] == 2
