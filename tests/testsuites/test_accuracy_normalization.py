"""Accuracy 归一化与别名支持测试。"""

from __future__ import annotations

import pytest

from vllm_cibench.testsuites.accuracy import run_accuracy


@pytest.mark.accuracy
def test_case_insensitive_and_strip(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    payload = {"choices": [{"message": {"content": "  Paris  "}}]}
    requests_mock.post(url, json=payload, status_code=200)

    cfg = {
        "task": "dummy",
        "case_insensitive": True,
        "strip": True,
        "samples": [{"question": "Capital?", "choices": ["paris"], "answer": "PARIS"}],
    }
    out = run_accuracy(base_url=base, model="dummy", cfg=cfg)
    assert out["correct"] == 1 and out["total"] == 1


@pytest.mark.accuracy
def test_answer_aliases(requests_mock):
    base = "http://example.com/v1"
    url = base + "/chat/completions"
    payload = {"choices": [{"message": {"content": "NYC"}}]}
    requests_mock.post(url, json=payload, status_code=200)

    cfg = {
        "task": "dummy",
        "samples": [
            {
                "question": "City?",
                "choices": ["New York", "NYC"],
                "answer": "New York",
                "answer_aliases": ["NYC", "New-York"],
            }
        ],
    }
    out = run_accuracy(base_url=base, model="dummy", cfg=cfg)
    assert out["correct"] == 1 and out["total"] == 1
