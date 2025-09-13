"""Accuracy max_samples 配置测试。"""

from __future__ import annotations

import pytest

from vllm_cibench.testsuites.accuracy import run_accuracy


@pytest.mark.accuracy
def test_run_accuracy_respects_max_samples(requests_mock):
    """当配置了 max_samples 时，仅评测前 N 条样本。"""

    base = "http://example.com/v1"
    url = base + "/chat/completions"
    # 准备 3 次响应，但期望只请求 1 次
    payload = {"choices": [{"message": {"content": "A"}}]}
    requests_mock.post(
        url,
        [
            {"json": payload, "status_code": 200},
            {"json": payload, "status_code": 200},
            {"json": payload, "status_code": 200},
        ],
    )

    cfg = {
        "task": "gpqa",
        "max_samples": 1,
        "samples": [
            {"question": "q1", "choices": ["A"], "answer": "A"},
            {"question": "q2", "choices": ["B"], "answer": "B"},
            {"question": "q3", "choices": ["C"], "answer": "C"},
        ],
    }
    out = run_accuracy(base_url=base, model="dummy", cfg=cfg)
    # 仅评测 1 条
    assert out["total"] == 1 and out["correct"] == 1
    # requests_mock 只应收到一次请求
    assert len(requests_mock.request_history) == 1
