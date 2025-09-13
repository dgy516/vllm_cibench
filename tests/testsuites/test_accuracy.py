"""Accuracy 执行器测试。"""

from __future__ import annotations

import pytest

from vllm_cibench.testsuites.accuracy import run_accuracy


@pytest.mark.accuracy
def test_run_accuracy_basic(requests_mock):
    """两条样本各答一次，计算正确率。"""

    base = "http://example.com/v1"
    url = base + "/chat/completions"
    # 模拟第一次回答正确，第二次回答错误
    payload_ok = {
        "choices": [{"message": {"content": "4"}}],
    }
    payload_bad = {
        "choices": [{"message": {"content": "3"}}],
    }
    requests_mock.post(
        url,
        [
            {"json": payload_ok, "status_code": 200},
            {"json": payload_bad, "status_code": 200},
        ],
    )

    cfg = {
        "task": "gpqa",
        "samples": [
            {"question": "2+2?", "choices": ["3", "4"], "answer": "4"},
            {"question": "1+1?", "choices": ["2", "3"], "answer": "2"},
        ],
    }
    out = run_accuracy(base_url=base, model="dummy", cfg=cfg)
    assert out["task"] == "gpqa"
    assert out["correct"] == 1 and out["total"] == 2
    assert abs(out["score"] - 0.5) < 1e-9


@pytest.mark.accuracy
def test_run_accuracy_http_error(requests_mock):
    """服务返回 4xx/5xx 时，应抛出 HTTPError 由上层捕获。"""

    base = "http://example.com/v1"
    url = base + "/chat/completions"
    requests_mock.post(url, status_code=500, json={"error": {"message": "boom"}})

    with pytest.raises(Exception):
        run_accuracy(
            base_url=base,
            model="dummy",
            cfg={
                "samples": [
                    {"question": "x?", "choices": ["y"], "answer": "y"},
                ]
            },
        )
