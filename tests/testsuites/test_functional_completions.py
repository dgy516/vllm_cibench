"""Completions 端点功能测试。"""

from __future__ import annotations

import pytest

from vllm_cibench.testsuites.functional import run_basic_completion


@pytest.mark.functional
def test_completions_basic(requests_mock):
    """基础 completions：应返回 choices[0].text。"""

    base = "http://example.com/v1"
    url = base + "/completions"
    payload = {
        "id": "cmpl-xyz",
        "object": "text_completion",
        "created": 0,
        "model": "dummy",
        "choices": [{"index": 0, "text": "Hello", "finish_reason": "stop"}],
    }
    requests_mock.post(url, json=payload, status_code=200)

    out = run_basic_completion(base_url=base, model="dummy", prompt="Hi")
    assert out["choices"][0]["text"] == "Hello"


@pytest.mark.functional
def test_completions_stream(requests_mock):
    """stream 模式应返回按顺序排列的 chunk（text 字段）。"""

    base = "http://example.com/v1"
    url = base + "/completions"
    content = (
        'data: {"choices":[{"index":0,"text":"He"}]}\n\n'
        'data: {"choices":[{"index":0,"text":"llo"}]}\n\n'
        "data: [DONE]\n\n"
    )
    requests_mock.post(
        url,
        content=content.encode(),
        headers={"Content-Type": "text/event-stream"},
        status_code=200,
    )

    out = run_basic_completion(base_url=base, model="dummy", prompt="Hi", stream=True)
    assert isinstance(out, list) and len(out) == 2
    assert out[0]["choices"][0]["text"] == "He"
    assert out[1]["choices"][0]["text"] == "llo"
