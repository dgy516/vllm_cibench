"""Reasoning 负路径：缺少 reasoning_content 字段。"""

from __future__ import annotations

import pytest

from vllm_cibench.testsuites.functional import get_reasoning


@pytest.mark.functional
def test_reasoning_missing_key_raises():
    out = {
        "id": "chatcmpl-xyz",
        "object": "chat.completion",
        "created": 0,
        "model": "dummy",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": "ok"}},
        ],
    }
    with pytest.raises(KeyError):
        _ = get_reasoning(out)
