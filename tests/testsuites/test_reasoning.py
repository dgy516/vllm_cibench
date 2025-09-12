"""Reasoning 功能测试。"""

from __future__ import annotations

import json

from vllm_cibench.clients.openai_client import OpenAICompatClient
from vllm_cibench.testsuites.functional import get_reasoning, run_basic_chat


def _fake_reasoning_resp() -> dict:
    """构造包含推理字段的响应。"""

    return {
        "id": "chatcmpl-xyz",
        "object": "chat.completion",
        "created": 0,
        "model": "dummy",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "ok",
                    "reasoning_content": "chain",
                },
                "finish_reason": "stop",
            }
        ],
    }


def test_reasoning_content(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    requests_mock.post(url, json=_fake_reasoning_resp(), status_code=200)

    client = OpenAICompatClient(base_url=base)
    out = run_basic_chat(
        client,
        model="dummy",
        messages=[{"role": "user", "content": "hi"}],
        reasoning=True,
    )
    body = json.loads(requests_mock.request_history[0].text)
    assert body["reasoning"] is True
    rc = get_reasoning(out)
    assert rc == "chain"
